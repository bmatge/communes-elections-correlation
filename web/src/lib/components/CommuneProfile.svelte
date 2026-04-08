<script lang="ts">
	import { query, queryOne } from '$lib/db';

	let { code }: { code: string } = $props();

	type CommuneInfo = {
		code_commune: string;
		libelle: string;
		code_departement: string;
		code_region: string;
		population: number;
		superficie: number;
		densite: number;
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
		display: boolean;
		relative_id: string | null;
	};

	type ClusterInfo = { cluster_id: number; cluster_label: string };
	type Residual = { target: string; residual_std: number };
	type ZScore = { variable_id: string; zscore: number };

	let categoryMode: Record<string, 'relative' | 'absolute'> = $state({});

	const CATEGORY_LABELS: Record<string, string> = {
		revenus: 'Revenus',
		emploi: 'Emploi',
		logement: 'Logement',
		education: 'Education',
		territoire: 'Territoire',
		securite: 'Securite',
		sante: 'Sante',
		vie_locale: 'Vie locale',
		transport: 'Transport',
		electoral: 'Electoral'
	};

	const CATEGORY_ORDER = Object.keys(CATEGORY_LABELS);

	const FAMILY_COLORS: Record<string, string> = {
		gauche: 'var(--color-gauche)',
		centre: 'var(--color-centre)',
		droite: 'var(--color-droite)',
		extreme_droite: 'var(--color-exd)',
		exd: 'var(--color-exd)'
	};

	let commune = $state<CommuneInfo | null>(null);
	let variables = $state<Variable[]>([]);
	let cluster = $state<ClusterInfo | null>(null);
	let residuals = $state<Residual[]>([]);
	let topZscores = $state<ZScore[]>([]);
	let loading = $state(true);

	// All displayable variables (hide denominators)
	let displayVars = $derived(variables.filter((v) => v.display !== false));

	// Set of variable_ids that are relative counterparts of some absolute
	let relativeIds = $derived(new Set(variables.filter((v) => v.relative_id).map((v) => v.relative_id)));

	// Check if a category has any relative/absolute pairs
	function catHasToggle(cat: string): boolean {
		return displayVars.some((v) => v.category === cat && v.relative_id);
	}

	function varsForCategory(cat: string): Variable[] {
		const mode = categoryMode[cat] ?? 'relative';
		const catVars = displayVars.filter((v) => v.category === cat);

		return catVars.filter((v) => {
			if (mode === 'relative' && v.relative_id) {
				// Hide absolute if its relative counterpart exists in data
				return !catVars.some((rv) => rv.variable_id === v.relative_id);
			}
			if (mode === 'absolute' && relativeIds.has(v.variable_id)) {
				// Hide computed percentage
				return false;
			}
			return true;
		});
	}

	let grouped = $derived(
		CATEGORY_ORDER.filter((cat) => displayVars.some((v) => v.category === cat)).map((cat) => ({
			category: cat,
			label: CATEGORY_LABELS[cat] || cat,
			hasToggle: catHasToggle(cat),
			vars: varsForCategory(cat)
		}))
	);

	let electoralScores = $derived(
		variables
			.filter((v) => v.category === 'electoral' && v.variable_id.includes('score_'))
			.filter((v) => v.variable_id.includes('pres22t1'))
			.sort((a, b) => b.value - a.value)
	);

	$effect(() => {
		if (!code) return;
		loading = true;

		Promise.all([
			queryOne<CommuneInfo>(
				`SELECT code_commune, libelle, code_departement, code_region, population, superficie, densite, code_epci, libelle_epci
				 FROM communes WHERE code_commune = '${code}'`
			),
			query<Variable>(
				`SELECT vm.variable_id, vm.name, vm.category, vm.unit,
				        cd.value,
				        med.median_val AS national_median,
				        med.min_val AS national_min,
				        med.max_val AS national_max,
				        vm.display,
				        vm.relative_id
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
			),
			queryOne<ClusterInfo>(
				`SELECT cc.cluster_id, cp.cluster_label
				 FROM commune_clusters cc
				 LEFT JOIN (
				     SELECT cluster_id, cluster_label FROM cluster_profiles LIMIT 20
				 ) cp ON cc.cluster_id = cp.cluster_id
				 WHERE cc.code_commune = '${code}'`
			).catch(() => null),
			query<Residual>(
				`SELECT target, residual_std FROM commune_residuals
				 WHERE code_commune = '${code}'
				 ORDER BY ABS(residual_std) DESC`
			).catch(() => []),
			query<ZScore>(
				`SELECT variable_id, zscore FROM commune_zscores
				 WHERE code_commune = '${code}'
				 ORDER BY ABS(zscore) DESC LIMIT 10`
			).catch(() => [])
		]).then(([c, v, cl, res, zs]) => {
			commune = c;
			variables = v;
			cluster = cl;
			residuals = res;
			topZscores = zs;
			loading = false;
		});
	});

	function formatValue(val: number | null, unit: string): string {
		if (val === null || val === undefined) return '—';
		if (unit === '%' || unit === 'pct') return val.toFixed(1) + ' %';
		if (unit === 'euros') return val.toLocaleString('fr-FR', { maximumFractionDigits: 0 }) + ' euros';
		if (Number.isInteger(val) || Math.abs(val) >= 100)
			return val.toLocaleString('fr-FR', { maximumFractionDigits: 0 });
		return val.toLocaleString('fr-FR', { maximumFractionDigits: 2 });
	}

	function barPosition(val: number, min: number, max: number): number {
		if (max === min) return 50;
		return Math.max(2, Math.min(98, ((val - min) / (max - min)) * 100));
	}

	function familyColor(varId: string): string {
		for (const [key, color] of Object.entries(FAMILY_COLORS)) {
			if (varId.includes(key)) return color;
		}
		return 'var(--color-accent)';
	}

	function formatResidual(val: number): string {
		const sign = val >= 0 ? '+' : '';
		return sign + val.toFixed(1) + ' sigma';
	}
</script>

{#if loading}
	<div class="loading">
		<span>Chargement...</span>
	</div>
{:else if !commune}
	<div class="empty">
		<p>Commune introuvable.</p>
	</div>
{:else}
	<header class="commune-header">
		<div class="header-top">
			<div>
				<h1>{commune.libelle}</h1>
				<div class="meta">
					<span class="code">{commune.code_commune}</span>
					<span class="sep">.</span>
					<span>Dep. {commune.code_departement}</span>
					{#if commune.population}
						<span class="sep">.</span>
						<span>{commune.population.toLocaleString('fr-FR')} hab.</span>
					{/if}
					{#if commune.superficie}
						<span class="sep">.</span>
						<span>{commune.superficie} km2</span>
					{/if}
					{#if commune.densite}
						<span class="sep">.</span>
						<span>{commune.densite.toLocaleString('fr-FR')} hab/km2</span>
					{/if}
				</div>
				{#if commune.libelle_epci}
					<div class="epci">{commune.libelle_epci}</div>
				{/if}
			</div>
			{#if cluster}
				<div class="cluster-badge">
					<span class="cluster-label">{cluster.cluster_label || `Cluster ${cluster.cluster_id}`}</span>
				</div>
			{/if}
		</div>
	</header>

	<!-- Electoral radar — scores pres22 by family -->
	{#if electoralScores.length > 0}
		<section class="section electoral-summary">
			<h2>Presidentielles 2022 — 1er tour</h2>
			<div class="score-bars">
				{#each electoralScores as s}
					<div class="score-row">
						<span class="score-label">{s.name.replace('Score ', '').replace(' Pres22T1', '')}</span>
						<div class="score-track">
							<div
								class="score-fill"
								style:width="{Math.min(s.value, 100)}%"
								style:background={familyColor(s.variable_id)}
							></div>
						</div>
						<span class="score-val">{s.value.toFixed(1)}%</span>
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Residuals — anomalies -->
	{#if residuals.length > 0}
		<section class="section">
			<h2>Anomalies electorales</h2>
			<p class="section-desc">Ecart entre le score observe et le score predit par le profil socio-eco</p>
			<div class="residuals-grid">
				{#each residuals as r}
					<div class="residual-card" class:positive={r.residual_std > 0} class:negative={r.residual_std < 0}>
						<span class="residual-target">{r.target.replace(/_/g, ' ')}</span>
						<span class="residual-value">{formatResidual(r.residual_std)}</span>
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Z-scores — deviation from department -->
	{#if topZscores.length > 0}
		<section class="section">
			<h2>Ecarts departementaux</h2>
			<p class="section-desc">Variables ou cette commune devie le plus de la moyenne de son departement</p>
			<div class="zscores-list">
				{#each topZscores as z}
					<div class="zscore-row">
						<span class="zscore-name">{z.variable_id.replace(/_/g, ' ')}</span>
						<div class="zscore-bar-track">
							{#if z.zscore >= 0}
								<div class="zscore-bar right" style:width="{Math.min(Math.abs(z.zscore) * 15, 50)}%"></div>
							{:else}
								<div class="zscore-bar left" style:width="{Math.min(Math.abs(z.zscore) * 15, 50)}%"></div>
							{/if}
						</div>
						<span class="zscore-val" class:positive={z.zscore > 0} class:negative={z.zscore < 0}>
							{z.zscore >= 0 ? '+' : ''}{z.zscore.toFixed(1)}
						</span>
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- All variables by category -->
	<div class="categories">
		{#each grouped as group}
			<details class="category" open={group.category === 'revenus' || group.category === 'emploi'}>
				<summary>
					<h2>{group.label}</h2>
					<span class="cat-count">{group.vars.length}</span>
					<svg class="chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
				</summary>
				{#if group.hasToggle}
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div class="mode-toggle" onclick={(e) => e.stopPropagation()}>
						<button
							class:active={(categoryMode[group.category] ?? 'relative') === 'relative'}
							onclick={() => (categoryMode[group.category] = 'relative')}
						>%</button>
						<button
							class:active={(categoryMode[group.category] ?? 'relative') === 'absolute'}
							onclick={() => (categoryMode[group.category] = 'absolute')}
						>n</button>
					</div>
				{/if}
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
										style:background={v.category === 'electoral' ? familyColor(v.variable_id) : 'var(--color-accent)'}
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
			</details>
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

	.header-top {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--spacing-md);
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

	.epci {
		margin-top: 4px;
		font-size: 0.75rem;
		color: var(--color-text-dim);
	}

	.cluster-badge {
		background: var(--color-surface-raised);
		border: 1px solid var(--color-border);
		border-radius: 20px;
		padding: 6px 16px;
		flex-shrink: 0;
	}

	.cluster-label {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--color-accent);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	/* Sections */
	.section {
		margin-bottom: var(--spacing-xl);
	}

	.section h2 {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--color-accent);
		margin-bottom: var(--spacing-md);
		padding-bottom: var(--spacing-xs);
		border-bottom: 1px solid var(--color-border);
	}

	/* Accordéons catégorie */
	.category {
		border: 1px solid var(--color-border);
		border-radius: 8px;
		overflow: hidden;
	}

	.category summary {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		padding: 12px 16px;
		cursor: pointer;
		background: var(--color-surface);
		transition: background 0.12s;
		list-style: none;
	}

	.category summary::-webkit-details-marker { display: none; }

	.category summary:hover {
		background: var(--color-surface-raised);
	}

	.category summary h2 {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--color-accent);
		margin: 0;
		padding: 0;
		border: none;
		flex: 1;
	}

	.cat-count {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--color-text-dim);
		background: var(--color-surface-raised);
		padding: 1px 7px;
		border-radius: 99px;
	}

	.chevron {
		color: var(--color-text-dim);
		transition: transform 0.2s;
		flex-shrink: 0;
	}

	.category[open] > summary .chevron {
		transform: rotate(180deg);
	}

	.category > .vars-grid {
		padding: 0 16px 16px;
	}

	.section-desc {
		font-size: 0.75rem;
		color: var(--color-text-dim);
		margin-bottom: var(--spacing-md);
		margin-top: -8px;
	}

	/* Electoral scores */
	.score-bars {
		display: flex;
		flex-direction: column;
		gap: 8px;
		max-width: 500px;
	}

	.score-row {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.score-label {
		font-size: 0.75rem;
		color: var(--color-text-muted);
		width: 120px;
		flex-shrink: 0;
		text-align: right;
	}

	.score-track {
		flex: 1;
		height: 14px;
		background: var(--color-surface);
		border-radius: 3px;
		overflow: hidden;
	}

	.score-fill {
		height: 100%;
		border-radius: 3px;
		transition: width 0.3s ease;
	}

	.score-val {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--color-text);
		width: 50px;
		text-align: right;
	}

	/* Residuals */
	.residuals-grid {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}

	.residual-card {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 6px;
		padding: 10px 16px;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.residual-card.positive {
		border-left: 3px solid var(--color-gauche);
	}

	.residual-card.negative {
		border-left: 3px solid var(--color-droite);
	}

	.residual-target {
		font-size: 0.75rem;
		color: var(--color-text-muted);
		text-transform: capitalize;
	}

	.residual-value {
		font-family: var(--font-mono);
		font-size: 0.9rem;
		font-weight: 700;
	}

	.residual-card.positive .residual-value {
		color: var(--color-gauche);
	}

	.residual-card.negative .residual-value {
		color: var(--color-droite);
	}

	/* Z-scores */
	.zscores-list {
		display: flex;
		flex-direction: column;
		gap: 6px;
		max-width: 600px;
	}

	.zscore-row {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.zscore-name {
		font-size: 0.75rem;
		color: var(--color-text-muted);
		width: 180px;
		flex-shrink: 0;
		text-align: right;
		text-transform: capitalize;
	}

	.zscore-bar-track {
		flex: 1;
		height: 8px;
		background: var(--color-surface);
		border-radius: 4px;
		position: relative;
		display: flex;
		justify-content: center;
	}

	.zscore-bar {
		height: 100%;
		border-radius: 4px;
		position: absolute;
		top: 0;
	}

	.zscore-bar.right {
		left: 50%;
		background: var(--color-accent);
	}

	.zscore-bar.left {
		right: 50%;
		background: var(--color-gauche);
	}

	.zscore-val {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		width: 45px;
		text-align: right;
	}

	.zscore-val.positive {
		color: var(--color-accent);
	}

	.zscore-val.negative {
		color: var(--color-gauche);
	}

	/* Toggle absolu / relatif (dans l'accordéon) */
	.mode-toggle {
		display: flex;
		gap: 1px;
		background: var(--color-surface-raised);
		border: 1px solid var(--color-border);
		border-radius: 4px;
		padding: 1px;
		width: fit-content;
		margin: 8px 16px 0;
	}

	.mode-toggle button {
		background: none;
		border: none;
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--color-text-dim);
		padding: 3px 10px;
		border-radius: 3px;
		cursor: pointer;
		transition: all 0.15s;
		font-weight: 700;
	}

	.mode-toggle button.active {
		background: var(--color-accent);
		color: var(--color-accent-text);
	}

	/* Variable cards */
	.categories {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xl);
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

	@media (max-width: 768px) {
		.commune-header h1 {
			font-size: 1.75rem;
		}

		.header-top {
			flex-direction: column;
		}

		.score-label,
		.zscore-name {
			width: 80px;
			font-size: 0.65rem;
		}

		.vars-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
