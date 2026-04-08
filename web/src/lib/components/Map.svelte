<script lang="ts">
	import { onMount } from 'svelte';
	import maplibregl from 'maplibre-gl';
	import 'maplibre-gl/dist/maplibre-gl.css';
	import { query } from '$lib/db';

	let {
		variableId = $bindable('revenu_median'),
		onCommuneClick
	}: {
		variableId?: string;
		onCommuneClick?: (code: string) => void;
	} = $props();

	let mapContainer: HTMLDivElement;
	let map: maplibregl.Map | null = $state(null);
	let loading = $state(true);
	let popup: maplibregl.Popup | null = null;
	let communesGeoJSON: GeoJSON.FeatureCollection | null = null;
	let legendMin = $state('');
	let legendMax = $state('');
	let legendLabel = $state('');
	let legendPalette = $state<string[]>([]);

	type PaletteId = 'gauche' | 'droite' | 'exd' | 'centre' | 'abstention' | 'neutral' | 'diverging';

	const PALETTES: Record<PaletteId, string[]> = {
		gauche: ['#1a1a2e', '#5c1528', '#a12040', '#e02e4e', '#ff3b5c'],
		droite: ['#1a1a2e', '#1c3058', '#1e5090', '#2970c8', '#3a86ff'],
		exd: ['#1a1a2e', '#2d1654', '#4e2388', '#6f30bc', '#8338ec'],
		centre: ['#1a1a2e', '#3d2e00', '#7a5c00', '#b88d00', '#ffbe0b'],
		abstention: ['#1a3a1a', '#2d5a2d', '#606040', '#9a7040', '#d44020'],
		neutral: ['#1a1a2e', '#2563eb', '#60a5fa', '#fbbf24', '#ffbe0b'],
		diverging: ['#3a86ff', '#8090a0', '#2a2a32', '#a05080', '#ff3b5c']
	};

	function detectPalette(varId: string): PaletteId {
		if (varId.includes('score_gauche')) return 'gauche';
		if (varId.includes('score_extreme_droite')) return 'exd';
		if (varId.includes('score_droite')) return 'droite';
		if (varId.includes('score_centre')) return 'centre';
		if (varId.includes('abstention')) return 'abstention';
		if (varId.includes('residual')) return 'diverging';
		return 'neutral';
	}

	function getColorStops(min: number, max: number, palette: string[]): [number, string][] {
		const range = max - min || 1;
		const n = palette.length;
		return palette.map((color, i) => [min + (range * i) / (n - 1), color] as [number, string]);
	}

	function formatLegendValue(val: number, varId: string): string {
		if (varId.includes('pct_') || varId.includes('score_') || varId.includes('taux_')) {
			return val.toFixed(1) + '%';
		}
		if (varId.includes('revenu') || varId.includes('loyer') || varId.includes('prix')) {
			return val.toLocaleString('fr-FR', { maximumFractionDigits: 0 }) + '€';
		}
		if (varId.includes('residual')) {
			return (val >= 0 ? '+' : '') + val.toFixed(1) + 'σ';
		}
		return val.toLocaleString('fr-FR', { maximumFractionDigits: 1 });
	}

	async function loadGeoJSON(): Promise<GeoJSON.FeatureCollection> {
		const rows = await query<{
			code_commune: string;
			nom: string;
			geometry: string;
		}>('SELECT code_commune, nom, geometry FROM geo_communes_lowres');

		const features: GeoJSON.Feature[] = rows.map((r) => ({
			type: 'Feature' as const,
			properties: {
				code: r.code_commune,
				nom: r.nom,
				value: 0
			},
			geometry: JSON.parse(r.geometry)
		}));

		return { type: 'FeatureCollection' as const, features };
	}

	async function loadDepartements(): Promise<GeoJSON.FeatureCollection> {
		const rows = await query<{ code_departement: string; nom: string; geometry: string }>(
			'SELECT code_departement, nom, geometry FROM geo_departements'
		);
		return {
			type: 'FeatureCollection' as const,
			features: rows.map((r) => ({
				type: 'Feature' as const,
				properties: { code: r.code_departement, nom: r.nom },
				geometry: JSON.parse(r.geometry)
			}))
		};
	}

	async function updateChoropleth(varId: string) {
		if (!map || !communesGeoJSON) return;

		// Detect data source — commune_data or analysis tables
		let sql: string;
		if (varId.startsWith('residual_')) {
			const target = varId.replace('residual_', '');
			sql = `SELECT code_commune, residual_std AS value FROM commune_residuals WHERE target = '${target}'`;
		} else if (varId === 'cluster_id') {
			sql = `SELECT code_commune, CAST(cluster_id AS DOUBLE) AS value FROM commune_clusters`;
		} else if (varId.startsWith('zscore_')) {
			const target = varId.replace('zscore_', '');
			sql = `SELECT code_commune, zscore AS value FROM commune_zscores WHERE variable_id = '${target}'`;
		} else {
			sql = `SELECT code_commune, value FROM commune_data WHERE variable_id = '${varId}'`;
		}

		const rows = await query<{ code_commune: string; value: number }>(sql);
		const values = new Map(rows.map((r) => [r.code_commune, r.value]));

		let min = Infinity;
		let max = -Infinity;

		for (const feat of communesGeoJSON.features) {
			const val = values.get(feat.properties!.code);
			if (val !== undefined && val !== null) {
				feat.properties!.value = val;
				if (val < min) min = val;
				if (val > max) max = val;
			} else {
				feat.properties!.value = null;
			}
		}

		const source = map.getSource('communes') as maplibregl.GeoJSONSource;
		source.setData(communesGeoJSON);

		if (min === Infinity) return;

		// For diverging palettes (residuals, z-scores), center on 0
		if (varId.includes('residual') || varId.includes('zscore')) {
			const absMax = Math.max(Math.abs(min), Math.abs(max));
			min = -absMax;
			max = absMax;
		}

		const paletteId = detectPalette(varId);
		const palette = PALETTES[paletteId];
		const stops = getColorStops(min, max, palette);

		map.setPaintProperty('communes-fill', 'fill-color', [
			'interpolate',
			['linear'],
			['coalesce', ['get', 'value'], min],
			...stops.flat()
		]);

		// Update legend
		legendMin = formatLegendValue(min, varId);
		legendMax = formatLegendValue(max, varId);
		legendPalette = palette;
		legendLabel = varId.replace(/_/g, ' ');
	}

	onMount(() => {
		map = new maplibregl.Map({
			container: mapContainer,
			style: {
				version: 8,
				sources: {},
				layers: [
					{
						id: 'background',
						type: 'background',
						paint: { 'background-color': '#0c0c0f' }
					}
				]
			},
			center: [2.5, 46.5],
			zoom: 5.5,
			maxBounds: [
				[-10, 40],
				[15, 52]
			]
		});

		map.addControl(new maplibregl.NavigationControl(), 'top-right');

		map.on('load', async () => {
			const [geo, deptsGeo] = await Promise.all([loadGeoJSON(), loadDepartements()]);
			communesGeoJSON = geo;

			map!.addSource('communes', { type: 'geojson', data: communesGeoJSON });
			map!.addLayer({
				id: 'communes-fill',
				type: 'fill',
				source: 'communes',
				paint: {
					'fill-color': '#2a2a32',
					'fill-opacity': 0.9
				}
			});
			map!.addLayer({
				id: 'communes-line',
				type: 'line',
				source: 'communes',
				paint: {
					'line-color': '#2a2a32',
					'line-width': ['interpolate', ['linear'], ['zoom'], 5, 0, 9, 0.5]
				}
			});

			map!.addSource('departements', { type: 'geojson', data: deptsGeo });
			map!.addLayer({
				id: 'departements-line',
				type: 'line',
				source: 'departements',
				paint: {
					'line-color': '#72728a',
					'line-width': ['interpolate', ['linear'], ['zoom'], 5, 0.5, 9, 1.5]
				}
			});

			map!.on('mousemove', 'communes-fill', (e) => {
				map!.getCanvas().style.cursor = 'pointer';
				const feat = e.features?.[0];
				if (!feat) return;
				const val = feat.properties.value;
				const display =
					val !== null && val !== undefined && val !== 'null'
						? formatLegendValue(Number(val), variableId)
						: '—';
				if (popup) popup.remove();
				popup = new maplibregl.Popup({ closeButton: false, offset: 10 })
					.setLngLat(e.lngLat)
					.setHTML(
						`<strong>${feat.properties.nom}</strong><br/>` +
							`<span style="font-family:var(--font-mono);font-size:0.8rem">${display}</span>`
					)
					.addTo(map!);
			});

			map!.on('mouseleave', 'communes-fill', () => {
				map!.getCanvas().style.cursor = '';
				if (popup) {
					popup.remove();
					popup = null;
				}
			});

			map!.on('click', 'communes-fill', (e) => {
				const feat = e.features?.[0];
				if (feat && onCommuneClick) {
					onCommuneClick(feat.properties.code);
				}
			});

			await updateChoropleth(variableId);
			loading = false;
			setTimeout(() => map?.resize(), 50);
		});

		return () => {
			map?.remove();
		};
	});

	$effect(() => {
		if (map && !loading) {
			updateChoropleth(variableId);
		}
	});
</script>

<div class="map-wrapper">
	{#if loading}
		<div class="loader">
			<span class="loader-text">Chargement des geometries...</span>
		</div>
	{/if}
	<div bind:this={mapContainer} class="map"></div>
	{#if legendPalette.length > 0}
		<div class="legend">
			<span class="legend-val">{legendMin}</span>
			<div class="legend-gradient" style:background="linear-gradient(to right, {legendPalette.join(', ')})"></div>
			<span class="legend-val">{legendMax}</span>
		</div>
	{/if}
</div>

<style>
	.map-wrapper {
		position: relative;
		width: 100%;
		height: 100%;
		border-radius: 8px;
		overflow: hidden;
		border: 1px solid var(--color-border);
	}

	.map {
		position: absolute;
		inset: 0;
	}

	.loader {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--color-bg);
		z-index: 10;
	}

	.loader-text {
		font-family: var(--font-mono);
		font-size: 0.8rem;
		color: var(--color-text-muted);
	}

	.legend {
		position: absolute;
		bottom: 16px;
		left: 16px;
		display: flex;
		align-items: center;
		gap: 8px;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 6px;
		padding: 8px 12px;
		z-index: 5;
	}

	.legend-gradient {
		width: 120px;
		height: 10px;
		border-radius: 3px;
	}

	.legend-val {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--color-text-muted);
		white-space: nowrap;
	}

	/* Override maplibre popup */
	:global(.maplibregl-popup-content) {
		background: var(--color-surface-raised) !important;
		color: var(--color-text) !important;
		border: 1px solid var(--color-border) !important;
		border-radius: 6px !important;
		padding: 8px 12px !important;
		font-family: var(--font-sans) !important;
		font-size: 0.85rem !important;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5) !important;
	}

	:global(.maplibregl-popup-tip) {
		border-top-color: var(--color-surface-raised) !important;
	}

	:global(.maplibregl-ctrl-group) {
		background: var(--color-surface) !important;
		border: 1px solid var(--color-border) !important;
	}

	:global(.maplibregl-ctrl-group button) {
		filter: invert(1);
	}
</style>
