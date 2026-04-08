<script lang="ts">
	import { query } from '$lib/db';
	import { goto } from '$app/navigation';

	type Row = {
		code_commune: string;
		libelle: string;
		code_departement: string;
		population: number;
		revenu_median: number | null;
		taux_chomage: number | null;
		pct_cadres: number | null;
		pct_diplomes_sup: number | null;
		pct_proprietaires: number | null;
		target: string;
		residual_std: number;
		predicted: number;
		actual: number;
		cluster_label: string | null;
	};

	type Target = { target: string; label: string };

	const TARGETS: Target[] = [
		{ target: 'score_gauche_pres22t1', label: 'Gauche — Pres. 2022' },
		{ target: 'score_extreme_droite_pres22t1', label: 'Extr. droite — Pres. 2022' },
		{ target: 'score_droite_pres22t1', label: 'Droite — Pres. 2022' },
		{ target: 'score_centre_pres22t1', label: 'Centre — Pres. 2022' },
		{ target: 'score_gauche_euro24t1', label: 'Gauche — Europ. 2024' },
		{ target: 'score_extreme_droite_euro24t1', label: 'Extr. droite — Europ. 2024' },
		{ target: 'score_gauche_legi24t1', label: 'Gauche — Légis. 2024' },
		{ target: 'score_extreme_droite_legi24t1', label: 'Extr. droite — Légis. 2024' },
		{ target: 'pct_abstention_pres22t1', label: 'Abstention — Pres. 2022' },
		{ target: 'pct_abstention_euro24t1', label: 'Abstention — Europ. 2024' }
	];

	let selectedTarget = $state('score_gauche_pres22t1');
	let minPop = $state(5000);
	let excludeDomTom = $state(true);
	let rows = $state<Row[]>([]);
	let loading = $state(true);

	const targetLabel = $derived(TARGETS.find((t) => t.target === selectedTarget)?.label ?? selectedTarget);

	function familyFromTarget(t: string): string {
		if (t.includes('gauche')) return 'gauche';
		if (t.includes('extreme_droite')) return 'exd';
		if (t.includes('droite')) return 'droite';
		if (t.includes('centre')) return 'centre';
		if (t.includes('abstention')) return 'abstention';
		return 'neutral';
	}

	const family = $derived(familyFromTarget(selectedTarget));

	async function loadData() {
		loading = true;
		const domFilter = excludeDomTom ? "AND c.code_departement NOT LIKE '97%' AND c.code_departement NOT LIKE '2A%' AND c.code_departement NOT LIKE '2B%'" : '';

		const sql = `
			WITH ranked AS (
				SELECT cr.code_commune, cr.target, cr.residual_std, cr.predicted,
				       cd_actual.value AS actual
				FROM commune_residuals cr
				JOIN commune_data cd_actual
				  ON cr.code_commune = cd_actual.code_commune
				 AND cr.target = cd_actual.variable_id
				WHERE cr.target = '${selectedTarget}'
			)
			SELECT r.code_commune, c.libelle, c.code_departement, c.population,
			       r.target, r.residual_std, r.predicted, r.actual,
			       rev.value AS revenu_median,
			       chom.value AS taux_chomage,
			       cad.value AS pct_cadres,
			       dip.value AS pct_diplomes_sup,
			       prop.value AS pct_proprietaires,
			       cp.cluster_label
			FROM ranked r
			JOIN communes c ON r.code_commune = c.code_commune
			LEFT JOIN commune_data rev ON r.code_commune = rev.code_commune AND rev.variable_id = 'revenu_median'
			LEFT JOIN commune_data chom ON r.code_commune = chom.code_commune AND chom.variable_id = 'taux_chomage'
			LEFT JOIN commune_data cad ON r.code_commune = cad.code_commune AND cad.variable_id = 'pct_cadres'
			LEFT JOIN commune_data dip ON r.code_commune = dip.code_commune AND dip.variable_id = 'pct_diplomes_sup'
			LEFT JOIN commune_data prop ON r.code_commune = prop.code_commune AND prop.variable_id = 'pct_proprietaires'
			LEFT JOIN commune_clusters cc ON r.code_commune = cc.code_commune
			LEFT JOIN (SELECT DISTINCT cluster_id, cluster_label FROM cluster_profiles) cp ON cc.cluster_id = cp.cluster_id
			WHERE c.population >= ${minPop}
			${domFilter}
			ORDER BY ABS(r.residual_std) DESC
			LIMIT 50
		`;

		try {
			rows = await query<Row>(sql);
		} catch {
			rows = [];
		}
		loading = false;
	}

	$effect(() => {
		// Re-run when filters change
		selectedTarget;
		minPop;
		excludeDomTom;
		loadData();
	});

	function fmt(val: number | null, suffix = ''): string {
		if (val === null || val === undefined) return '—';
		return val.toLocaleString('fr-FR', { maximumFractionDigits: 1 }) + suffix;
	}

	function sign(val: number): string {
		return val >= 0 ? '+' : '';
	}
</script>

<svelte:head>
	<title>Surprises — VoteSocio</title>
</svelte:head>

<div class="surprises-page">
	<header class="page-header">
		<p class="surtitle">Anomalies electorales</p>
		<h1>Les 50 communes<br /><em>qui ne rentrent pas dans la case</em></h1>
		<p class="intro">
			Communes dont le vote s'ecarte le plus de ce que leur profil socio-eco predit.
			Un residual de +3σ signifie un score 3 ecarts-types au-dessus du modele.
		</p>
	</header>

	<!-- Filters -->
	<div class="filters">
		<div class="filter">
			<label for="target">Variable electorale</label>
			<select id="target" bind:value={selectedTarget}>
				{#each TARGETS as t}
					<option value={t.target}>{t.label}</option>
				{/each}
			</select>
		</div>
		<div class="filter">
			<label for="pop">Population min.</label>
			<select id="pop" bind:value={minPop}>
				<option value={1000}>1 000</option>
				<option value={2000}>2 000</option>
				<option value={5000}>5 000</option>
				<option value={10000}>10 000</option>
				<option value={20000}>20 000</option>
				<option value={50000}>50 000</option>
			</select>
		</div>
		<label class="toggle-label">
			<input type="checkbox" bind:checked={excludeDomTom} />
			<span>Hors DOM-TOM / Corse</span>
		</label>
	</div>

	{#if loading}
		<div class="loading">Chargement...</div>
	{:else if rows.length === 0}
		<div class="loading">Aucun resultat pour ces filtres.</div>
	{:else}
		<!-- Table -->
		<div class="table-wrap">
			<table>
				<thead>
					<tr>
						<th class="rank">#</th>
						<th class="commune">Commune</th>
						<th class="num">Pop.</th>
						<th class="num">Revenu med.</th>
						<th class="num">Chomage</th>
						<th class="num">Cadres</th>
						<th class="num">Diplomes sup.</th>
						<th class="num">Proprio.</th>
						<th class="num predicted">Predit</th>
						<th class="num actual">Observe</th>
						<th class="num residual">Ecart</th>
					</tr>
				</thead>
				<tbody>
					{#each rows as row, i}
						<tr
							class="data-row"
							onclick={() => goto(`/commune?code=${row.code_commune}`)}
						>
							<td class="rank">{i + 1}</td>
							<td class="commune">
								<span class="name">{row.libelle}</span>
								<span class="dept">{row.code_departement}</span>
								{#if row.cluster_label}
									<span class="cluster">{row.cluster_label}</span>
								{/if}
							</td>
							<td class="num pop">{row.population?.toLocaleString('fr-FR')}</td>
							<td class="num">{fmt(row.revenu_median, '€')}</td>
							<td class="num">{fmt(row.taux_chomage, '%')}</td>
							<td class="num">{fmt(row.pct_cadres, '%')}</td>
							<td class="num">{fmt(row.pct_diplomes_sup, '%')}</td>
							<td class="num">{fmt(row.pct_proprietaires, '%')}</td>
							<td class="num predicted">{row.predicted.toFixed(1)}%</td>
							<td class="num actual {family}">{row.actual.toFixed(1)}%</td>
							<td class="num residual" class:positive={row.residual_std > 0} class:negative={row.residual_std < 0}>
								{sign(row.residual_std)}{row.residual_std.toFixed(1)}σ
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<div class="legend-bar">
			<span><strong>Predit</strong> = score attendu par le modele de regression (21 variables socio-eco)</span>
			<span><strong>Observe</strong> = score reel</span>
			<span><strong>Ecart</strong> = residual standardise (σ)</span>
		</div>
	{/if}
</div>

<style>
	.surprises-page {
		max-width: 1200px;
	}

	.page-header {
		margin-bottom: var(--spacing-xl);
	}

	.surtitle {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--color-accent);
		margin-bottom: var(--spacing-sm);
	}

	h1 {
		font-family: var(--font-display);
		font-size: 2.5rem;
		font-weight: 400;
		line-height: 1.15;
		margin-bottom: var(--spacing-md);
	}

	h1 em {
		color: var(--color-accent);
	}

	.intro {
		font-size: 0.88rem;
		color: var(--color-text-muted);
		line-height: 1.6;
		max-width: 600px;
	}

	/* Filters */
	.filters {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		gap: var(--spacing-md);
		margin-bottom: var(--spacing-lg);
		padding-bottom: var(--spacing-md);
		border-bottom: 1px solid var(--color-border);
	}

	.filter {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.filter label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--color-text-dim);
	}

	select {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 6px;
		color: var(--color-text);
		font-family: var(--font-sans);
		font-size: 0.82rem;
		padding: 8px 12px;
		cursor: pointer;
	}

	select:focus {
		outline: none;
		border-color: var(--color-accent);
	}

	.toggle-label {
		display: flex;
		align-items: center;
		gap: 6px;
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--color-text-muted);
		cursor: pointer;
		padding-bottom: 4px;
	}

	.toggle-label input {
		accent-color: var(--color-accent);
	}

	.loading {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 200px;
		font-family: var(--font-mono);
		font-size: 0.85rem;
		color: var(--color-text-muted);
	}

	/* Table */
	.table-wrap {
		overflow-x: auto;
		border: 1px solid var(--color-border);
		border-radius: 8px;
	}

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.78rem;
	}

	thead {
		position: sticky;
		top: 0;
		z-index: 2;
	}

	th {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--color-text-dim);
		background: var(--color-surface);
		padding: 10px 8px;
		text-align: left;
		white-space: nowrap;
		border-bottom: 1px solid var(--color-border);
	}

	th.num {
		text-align: right;
	}

	td {
		padding: 10px 8px;
		border-bottom: 1px solid var(--color-border);
		vertical-align: top;
	}

	.data-row {
		cursor: pointer;
		transition: background 0.1s;
	}

	.data-row:hover {
		background: var(--color-surface);
	}

	td.rank {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--color-text-dim);
		width: 30px;
		text-align: center;
	}

	td.commune {
		min-width: 160px;
	}

	.name {
		font-weight: 600;
		color: var(--color-text);
		display: block;
	}

	.dept {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--color-text-dim);
	}

	.cluster {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		color: var(--color-text-dim);
		background: var(--color-surface-raised);
		padding: 1px 6px;
		border-radius: 3px;
		margin-left: 4px;
	}

	td.num {
		font-family: var(--font-mono);
		text-align: right;
		color: var(--color-text-muted);
		white-space: nowrap;
	}

	td.pop {
		color: var(--color-text);
	}

	td.predicted {
		color: var(--color-text-dim);
	}

	td.actual.gauche { color: var(--color-gauche); }
	td.actual.exd { color: var(--color-exd); }
	td.actual.droite { color: var(--color-droite); }
	td.actual.centre { color: var(--color-centre); }
	td.actual.abstention { color: var(--color-text-muted); }

	th.predicted, th.actual, th.residual {
		border-left: 1px solid var(--color-border);
	}

	td.predicted, td.actual, td.residual {
		border-left: 1px solid var(--color-border);
	}

	td.residual {
		font-weight: 700;
		font-size: 0.85rem;
	}

	td.residual.positive {
		color: var(--color-accent);
	}

	td.residual.negative {
		color: var(--color-gauche);
	}

	.legend-bar {
		display: flex;
		flex-wrap: wrap;
		gap: var(--spacing-lg);
		margin-top: var(--spacing-md);
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--color-text-dim);
	}

	.legend-bar strong {
		color: var(--color-text-muted);
	}

	@media (max-width: 768px) {
		h1 { font-size: 1.75rem; }
		.filters { flex-direction: column; align-items: stretch; }
		table { font-size: 0.7rem; }
	}
</style>
