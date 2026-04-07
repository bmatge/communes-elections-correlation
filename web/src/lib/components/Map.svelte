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

	function getColorStops(min: number, max: number): [number, string][] {
		const range = max - min || 1;
		return [
			[min, '#1a1a2e'],
			[min + range * 0.2, '#2563eb'],
			[min + range * 0.4, '#60a5fa'],
			[min + range * 0.6, '#fbbf24'],
			[min + range * 0.8, '#f59e0b'],
			[max, '#ffbe0b']
		];
	}

	async function loadGeoJSON(): Promise<GeoJSON.FeatureCollection> {
		const rows = await query<{
			code_commune: string;
			nom: string;
			geometry: string;
		}>('SELECT code_commune, nom, geometry FROM geo_communes_lowres');

		console.log(`[Map] ${rows.length} communes chargées`);

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

		const rows = await query<{ code_commune: string; value: number }>(
			`SELECT code_commune, value FROM commune_data WHERE variable_id = '${varId}'`
		);
		const values = new Map(rows.map((r) => [r.code_commune, r.value]));
		console.log(`[Map] ${varId}: ${values.size} valeurs`);

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

		if (min === Infinity) {
			console.warn(`[Map] Aucune valeur pour ${varId}`);
			return;
		}

		console.log(`[Map] ${varId}: min=${min}, max=${max}`);

		const stops = getColorStops(min, max);
		map.setPaintProperty('communes-fill', 'fill-color', [
			'case',
			['==', ['get', 'value'], null],
			'#1e1e24',
			['interpolate', ['linear'], ['get', 'value'], ...stops.flat()]
		]);
	}

	onMount(async () => {
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

			// Communes layer
			map!.addSource('communes', { type: 'geojson', data: communesGeoJSON });
			map!.addLayer({
				id: 'communes-fill',
				type: 'fill',
				source: 'communes',
				paint: {
					'fill-color': '#1e1e24',
					'fill-opacity': 0.85
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

			// Départements overlay
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

			// Interactions
			map!.on('mousemove', 'communes-fill', (e) => {
				map!.getCanvas().style.cursor = 'pointer';
				const feat = e.features?.[0];
				if (!feat) return;
				const val = feat.properties.value;
				const display =
					val !== null && val !== undefined && val !== 'null'
						? Number(val).toLocaleString('fr-FR')
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
		});

		return () => {
			map?.remove();
		};
	});

	// React to variable changes
	$effect(() => {
		if (map && !loading) {
			updateChoropleth(variableId);
		}
	});
</script>

<div class="map-wrapper">
	{#if loading}
		<div class="loader">
			<span class="loader-text">Chargement des géométries…</span>
		</div>
	{/if}
	<div bind:this={mapContainer} class="map"></div>
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
		width: 100%;
		height: 100%;
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
