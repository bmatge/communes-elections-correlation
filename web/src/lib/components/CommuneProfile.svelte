<script lang="ts">
	import { query, queryOne } from '$lib/db';

	let { code }: { code: string } = $props();

	type CommuneInfo = {
		code_commune: string;
		libelle: string;
		code_departement: string;
		code_region: string;
		population: number;
		code_epci: string;
		libelle_epci: string;
	};

	type Variable = {
		variable_id: string;
		name: string;
		category: string;
		unit: string;
		value: number;
		national_median: number;
		national_min: number;
		national_max: number;
	};

	const CATEGORY_LABELS: Record<string, string> = {
		revenus: 'Revenus',
		emploi: 'Emploi',
		logement: 'Logement',
		education: 'Éducation',
		territoire: 'Territoire',
		securite: 'Sécurité',
		sante: 'Santé',
		vie_locale: 'Vie locale',
		transport: 'Transport',
		electoral: 'Électoral'
	};

	const CATEGORY_ORDER = Object.keys(CATEGORY_LABELS);

	let commune = $state<CommuneInfo | null>(null);
	let variables = $state<Variable[]>([]);
	let loading = $state(true);

	let grouped = $derived(
		CATEGORY_ORDER.filter((cat) => variables.some((v) => v.category === cat)).map((cat) => ({
			category: cat,
			label: CATEGORY_LABELS[cat] || cat,
			vars: variables.filter((v) => v.category === cat)
		}))
	);

	$effect(() => {
		if (!code) return;
		loading = true;

		Promise.all([
			queryOne<CommuneInfo>(
				`SELECT code_commune, libelle, code_departement, code_region, population, code_epci, libelle_epci
				 FROM communes WHERE code_commune = '${code}'`
			),
			query<Variable>(
				`SELECT vm.variable_id, vm.name, vm.category, vm.unit,
				        cd.value,
				        med.median_val AS national_median,
				        med.min_val AS national_min,
				        med.max_val AS national_max
				 FROM commune_data cd
				 JOIN variables_meta vm ON cd.variable_id = vm.variable_id
				 JOIN (
				     SELECT variable_id,
				            MEDIAN(value) AS median_val,
				            MIN(value) AS min_val,
				            MAX(value) AS max_val
				     FROM commune_data
				     GROUP BY variable_id
				 ) med ON cd.variable_id = med.variable_id
				 WHERE cd.code_commune = '${code}'
				   AND vm.type = 'numeric'
				 ORDER BY vm.category, vm.name`
			)
		]).then(([c, v]) => {
			commune = c;
			variables = v;
			loading = false;
		});
	});

	function formatValue(val: number | null, unit: string): string {
		if (val === null || val === undefined) return '—';
		if (unit === '%' || unit === 'pct') return val.toFixed(1) + ' %';
		if (unit === '€' || unit === 'euros') return val.toLocaleString('fr-FR', { maximumFractionDigits: 0 }) + ' €';
		if (Number.isInteger(val) || Math.abs(val) >= 100) return val.toLocaleString('fr-FR', { maximumFractionDigits: 0 });
		return val.toLocaleString('fr-FR', { maximumFractionDigits: 2 });
	}

	function barPosition(val: number, min: number, max: number): number {
		if (max === min) return 50;
		return Math.max(2, Math.min(98, ((val - min) / (max - min)) * 100));
	}
</script>

{#if loading}
	<div class="loading">
		<span>Chargement…</span>
	</div>
{:else if !commune}
	<div class="empty">
		<p>Commune introuvable.</p>
	</div>
{:else}
	<header class="commune-header">
		<h1>{commune.libelle}</h1>
		<div class="meta">
			<span class="code">{commune.code_commune}</span>
			<span class="sep">·</span>
			<span>Dép. {commune.code_departement}</span>
			{#if commune.population}
				<span class="sep">·</span>
				<span>{commune.population.toLocaleString('fr-FR')} hab.</span>
			{/if}
			{#if commune.libelle_epci}
				<span class="sep">·</span>
				<span class="epci">{commune.libelle_epci}</span>
			{/if}
		</div>
	</header>

	<div class="categories">
		{#each grouped as group}
			<section class="category">
				<h2>{group.label}</h2>
				<div class="vars-grid">
					{#each group.vars as v}
						<div class="var-row">
							<div class="var-info">
								<span class="var-name">{v.name}</span>
								<span class="var-value">{formatValue(v.value, v.unit)}</span>
							</div>
							<div class="var-bar">
								<div class="bar-track">
									<div
										class="bar-median"
										style:left="{barPosition(v.national_median, v.national_min, v.national_max)}%"
									></div>
									<div
										class="bar-dot"
										style:left="{barPosition(v.value, v.national_min, v.national_max)}%"
									></div>
								</div>
								<div class="bar-labels">
									<span>{formatValue(v.national_min, v.unit)}</span>
									<span>{formatValue(v.national_max, v.unit)}</span>
								</div>
							</div>
						</div>
					{/each}
				</div>
			</section>
		{/each}
	</div>
{/if}

<style>
	.loading,
	.empty {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 200px;
		font-family: var(--font-mono);
		font-size: 0.85rem;
		color: var(--color-text-muted);
	}

	.commune-header {
		padding-bottom: var(--spacing-lg);
		border-bottom: 1px solid var(--color-border);
		margin-bottom: var(--spacing-xl);
	}

	.commune-header h1 {
		font-family: var(--font-display);
		font-size: 2.5rem;
		font-weight: 400;
		line-height: 1.1;
	}

	.meta {
		margin-top: var(--spacing-sm);
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--color-text-muted);
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}

	.code {
		color: var(--color-accent);
	}

	.sep {
		opacity: 0.3;
	}

	.categories {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xl);
	}

	.category h2 {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--color-accent);
		margin-bottom: var(--spacing-md);
		padding-bottom: var(--spacing-xs);
		border-bottom: 1px solid var(--color-border);
	}

	.vars-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
		gap: var(--spacing-md);
	}

	.var-row {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 6px;
		padding: 12px 16px;
	}

	.var-info {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		margin-bottom: 8px;
	}

	.var-name {
		font-size: 0.8rem;
		color: var(--color-text-muted);
	}

	.var-value {
		font-family: var(--font-mono);
		font-size: 0.9rem;
		font-weight: 700;
		color: var(--color-text);
	}

	.var-bar {
		position: relative;
	}

	.bar-track {
		height: 4px;
		background: var(--color-surface-raised);
		border-radius: 2px;
		position: relative;
	}

	.bar-median {
		position: absolute;
		top: -3px;
		width: 1px;
		height: 10px;
		background: var(--color-text-dim);
		transform: translateX(-50%);
	}

	.bar-dot {
		position: absolute;
		top: -4px;
		width: 12px;
		height: 12px;
		background: var(--color-accent);
		border-radius: 50%;
		transform: translateX(-50%);
		box-shadow: 0 0 0 2px var(--color-surface);
	}

	.bar-labels {
		display: flex;
		justify-content: space-between;
		margin-top: 4px;
		font-family: var(--font-mono);
		font-size: 0.55rem;
		color: var(--color-text-dim);
	}
</style>
