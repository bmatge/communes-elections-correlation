<script lang="ts">
	import { query } from '$lib/db';

	type Coefficient = { target: string; feature: string; beta: number };
	type ScalerStat = { target: string; feature: string; feature_mean: number; feature_std: number };
	type ModelInfo = { target: string; r_squared: number };

	const TARGET_LABELS: Record<string, string> = {
		score_gauche_pres22t1: 'Gauche (Pres. 2022)',
		score_droite_pres22t1: 'Droite (Pres. 2022)',
		score_extreme_droite_pres22t1: 'Ext. droite (Pres. 2022)',
		score_centre_pres22t1: 'Centre (Pres. 2022)',
		pct_abstention_pres22t1: 'Abstention (Pres. 2022)',
		score_gauche_euro24t1: 'Gauche (Euro. 2024)',
		score_extreme_droite_euro24t1: 'Ext. droite (Euro. 2024)',
		pct_abstention_euro24t1: 'Abstention (Euro. 2024)',
		score_gauche_legi24t1: 'Gauche (Legi. 2024)',
		score_extreme_droite_legi24t1: 'Ext. droite (Legi. 2024)'
	};

	const TARGET_COLORS: Record<string, string> = {
		score_gauche_pres22t1: 'var(--color-gauche)',
		score_droite_pres22t1: 'var(--color-droite)',
		score_extreme_droite_pres22t1: 'var(--color-exd)',
		score_centre_pres22t1: 'var(--color-centre)',
		pct_abstention_pres22t1: 'var(--color-divers)',
		score_gauche_euro24t1: 'var(--color-gauche)',
		score_extreme_droite_euro24t1: 'var(--color-exd)',
		pct_abstention_euro24t1: 'var(--color-divers)',
		score_gauche_legi24t1: 'var(--color-gauche)',
		score_extreme_droite_legi24t1: 'var(--color-exd)'
	};

	const FEATURE_LABELS: Record<string, string> = {
		revenu_median: 'Revenu median',
		taux_pauvrete: 'Taux pauvrete',
		pct_diplomes_sup: '% diplomes sup.',
		pct_sans_diplome: '% sans diplome',
		pct_cadres: '% cadres',
		pct_ouvriers: '% ouvriers',
		pct_employes: '% employes',
		pct_agriculteurs: '% agriculteurs',
		pct_proprietaires: '% proprietaires',
		pct_hlm: '% HLM',
		pct_res_secondaires: '% res. secondaires',
		pct_logements_vacants: '% logements vacants',
		taux_chomage: 'Taux chomage',
		pct_etrangers: '% etrangers',
		pct_60plus: '% 60+ ans',
		pct_jeunes: '% jeunes (-14)',
		taux_fibre: 'Taux fibre',
		apl_medecins: 'APL medecins',
		equipements_total_1000hab: 'Equipements /1000 hab',
		taux_delinquance_1000: 'Delinquance /1000',
		loyer_median: 'Loyer median'
	};

	let coefficients = $state<Coefficient[]>([]);
	let scalerStats = $state<ScalerStat[]>([]);
	let models = $state<ModelInfo[]>([]);
	let sliderValues = $state<Record<string, number>>({});
	let features = $state<string[]>([]);
	let ready = $state(false);

	let predictions = $derived(computePredictions());

	function computePredictions(): { target: string; label: string; color: string; value: number }[] {
		if (!ready || features.length === 0) return [];

		const targets = [...new Set(coefficients.map((c) => c.target))];
		return targets.map((target) => {
			const coefs = coefficients.filter((c) => c.target === target);
			const stats = scalerStats.filter((s) => s.target === target);
			const intercept = coefs.find((c) => c.feature === '_intercept');

			let pred = intercept?.beta ?? 0;
			for (const stat of stats) {
				const coef = coefs.find((c) => c.feature === stat.feature);
				if (!coef || stat.feature_std === 0) continue;
				const rawVal = sliderValues[stat.feature] ?? stat.feature_mean;
				const scaled = (rawVal - stat.feature_mean) / stat.feature_std;
				pred += coef.beta * scaled;
			}

			return {
				target,
				label: TARGET_LABELS[target] || target,
				color: TARGET_COLORS[target] || 'var(--color-accent)',
				value: Math.max(0, Math.min(100, pred))
			};
		});
	}

	$effect(() => {
		Promise.all([
			query<Coefficient>('SELECT target, feature, beta FROM regression_results'),
			query<ScalerStat>('SELECT target, feature, feature_mean, feature_std FROM regression_scaler'),
			query<ModelInfo>(
				'SELECT DISTINCT target, r_squared FROM regression_results WHERE feature = \'_intercept\''
			)
		])
			.then(([c, s, m]) => {
				coefficients = c;
				scalerStats = s;
				models = m;

				// Get unique features from scaler stats
				const featureSet = new Set(s.map((x) => x.feature));
				features = [...featureSet];

				// Initialize sliders at mean values (from first target's stats)
				const firstTarget = s.length > 0 ? s[0].target : '';
				const vals: Record<string, number> = {};
				for (const stat of s.filter((x) => x.target === firstTarget)) {
					vals[stat.feature] = stat.feature_mean;
				}
				sliderValues = vals;
				ready = true;
			})
			.catch(() => {
				// Tables not available
			});
	});

	function getRange(feature: string): { min: number; max: number; step: number } {
		const stat = scalerStats.find((s) => s.feature === feature);
		if (!stat) return { min: 0, max: 100, step: 1 };
		const mean = stat.feature_mean;
		const std = stat.feature_std;
		// Range: mean +/- 3 std
		const min = Math.max(0, mean - 3 * std);
		const max = mean + 3 * std;
		const step = std > 100 ? 100 : std > 10 ? 1 : 0.1;
		return { min: Math.round(min * 10) / 10, max: Math.round(max * 10) / 10, step };
	}

	function formatSliderVal(feature: string, val: number): string {
		if (feature.includes('revenu') || feature.includes('loyer')) {
			return val.toLocaleString('fr-FR', { maximumFractionDigits: 0 }) + ' euros';
		}
		if (feature.includes('pct_') || feature.includes('taux_')) {
			return val.toFixed(1) + '%';
		}
		return val.toFixed(1);
	}

	function resetToMean() {
		const firstTarget = scalerStats.length > 0 ? scalerStats[0].target : '';
		const vals: Record<string, number> = {};
		for (const stat of scalerStats.filter((x) => x.target === firstTarget)) {
			vals[stat.feature] = stat.feature_mean;
		}
		sliderValues = vals;
	}
</script>

<svelte:head>
	<title>Simulateur — VoteSocio</title>
</svelte:head>

<div class="simulator-page">
	<header class="sim-header">
		<h1>Simulateur</h1>
		<p class="desc">
			Ajustez le profil socio-economique d'une commune fictive
			et observez les scores electoraux predits par la regression.
		</p>
	</header>

	{#if !ready}
		<div class="loading">Chargement des modeles...</div>
	{:else}
		<div class="sim-layout">
			<!-- Predictions panel -->
			<aside class="predictions-panel">
				<div class="predictions-header">
					<h2>Scores predits</h2>
					<button class="reset-btn" onclick={resetToMean}>Reinitialiser</button>
				</div>
				<div class="pred-cards">
					{#each predictions as pred}
						<div class="pred-card">
							<div class="pred-info">
								<span class="pred-label">{pred.label}</span>
								<span class="pred-value" style:color={pred.color}>
									{pred.value.toFixed(1)}%
								</span>
							</div>
							<div class="pred-bar-track">
								<div
									class="pred-bar-fill"
									style:width="{Math.min(pred.value, 100)}%"
									style:background={pred.color}
								></div>
							</div>
						</div>
					{/each}
				</div>
				<p class="model-info">
					{models.length} modeles OLS — R2 moyen {(
						models.reduce((s, m) => s + m.r_squared, 0) / models.length
					).toFixed(3)}
				</p>
			</aside>

			<!-- Sliders panel -->
			<div class="sliders-panel">
				<h2>Profil socio-economique</h2>
				<div class="sliders-grid">
					{#each features as feat}
						{@const range = getRange(feat)}
						<div class="slider-row">
							<div class="slider-header">
								<label class="slider-label" for="sl-{feat}">
									{FEATURE_LABELS[feat] || feat}
								</label>
								<span class="slider-val">
									{formatSliderVal(feat, sliderValues[feat] ?? range.min)}
								</span>
							</div>
							<input
								id="sl-{feat}"
								type="range"
								min={range.min}
								max={range.max}
								step={range.step}
								bind:value={sliderValues[feat]}
							/>
						</div>
					{/each}
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.simulator-page {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xl);
	}

	.sim-header h1 {
		font-family: var(--font-display);
		font-size: 1.75rem;
		font-weight: 400;
	}

	.desc {
		font-size: 0.85rem;
		color: var(--color-text-muted);
		line-height: 1.5;
		margin-top: var(--spacing-xs);
		max-width: 600px;
	}

	.loading {
		font-family: var(--font-mono);
		font-size: 0.85rem;
		color: var(--color-text-muted);
		padding: var(--spacing-xl);
		text-align: center;
	}

	.sim-layout {
		display: grid;
		grid-template-columns: 340px 1fr;
		gap: var(--spacing-xl);
		align-items: start;
	}

	/* Predictions */
	.predictions-panel {
		position: sticky;
		top: 80px;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: var(--spacing-lg);
	}

	.predictions-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--spacing-md);
	}

	.predictions-header h2 {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--color-accent);
	}

	.reset-btn {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--color-text-dim);
		background: transparent;
		border: 1px solid var(--color-border);
		border-radius: 4px;
		padding: 4px 10px;
		cursor: pointer;
		transition: all 0.15s;
	}

	.reset-btn:hover {
		color: var(--color-text);
		border-color: var(--color-text-dim);
	}

	.pred-cards {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.pred-card {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.pred-info {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
	}

	.pred-label {
		font-size: 0.75rem;
		color: var(--color-text-muted);
	}

	.pred-value {
		font-family: var(--font-mono);
		font-size: 1rem;
		font-weight: 700;
	}

	.pred-bar-track {
		height: 6px;
		background: var(--color-surface-raised);
		border-radius: 3px;
		overflow: hidden;
	}

	.pred-bar-fill {
		height: 100%;
		border-radius: 3px;
		transition: width 0.15s ease;
	}

	.model-info {
		margin-top: var(--spacing-md);
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--color-text-dim);
		text-align: center;
	}

	/* Sliders */
	.sliders-panel h2 {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--color-accent);
		margin-bottom: var(--spacing-lg);
		padding-bottom: var(--spacing-xs);
		border-bottom: 1px solid var(--color-border);
	}

	.sliders-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: var(--spacing-md);
	}

	.slider-row {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 6px;
		padding: 12px 16px;
	}

	.slider-header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		margin-bottom: 8px;
	}

	.slider-label {
		font-size: 0.8rem;
		color: var(--color-text-muted);
	}

	.slider-val {
		font-family: var(--font-mono);
		font-size: 0.8rem;
		font-weight: 700;
		color: var(--color-text);
	}

	input[type='range'] {
		appearance: none;
		-webkit-appearance: none;
		width: 100%;
		height: 4px;
		background: var(--color-surface-raised);
		border-radius: 2px;
		outline: none;
		cursor: pointer;
	}

	input[type='range']::-webkit-slider-thumb {
		-webkit-appearance: none;
		width: 16px;
		height: 16px;
		background: var(--color-accent);
		border-radius: 50%;
		cursor: pointer;
		box-shadow: 0 0 0 3px var(--color-surface);
	}

	input[type='range']::-moz-range-thumb {
		width: 16px;
		height: 16px;
		background: var(--color-accent);
		border-radius: 50%;
		border: none;
		cursor: pointer;
		box-shadow: 0 0 0 3px var(--color-surface);
	}

	@media (max-width: 768px) {
		.sim-layout {
			grid-template-columns: 1fr;
		}

		.predictions-panel {
			position: static;
		}

		.sliders-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
