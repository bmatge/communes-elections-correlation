<svelte:head>
	<title>Méthode — VoteSocio</title>
</svelte:head>

<article class="methode">
	<header class="page-header">
		<p class="surtitle">Transparence</p>
		<h1>Méthode</h1>
		<p class="intro">
			VoteSocio croise les résultats de 11 scrutins avec 200+ indicateurs socio-économiques
			pour 34 965 communes françaises. Tout est open data, tout est vérifiable.
		</p>
	</header>

	<!-- 1. OBJECTIF -->
	<section>
		<h2>Objectif</h2>
		<p>
			Cartographier les liens statistiques entre le profil socio-économique d'une commune
			(revenus, diplômes, CSP, logement, démographie) et ses résultats électoraux.
			Identifier les stéréotypes — et surtout leurs exceptions : les communes qui votent
			"autrement" que ce que leur profil prédit.
		</p>
		<div class="callout">
			<strong>Ecological fallacy.</strong> Les corrélations observées sont territoriales, pas individuelles.
			"Les communes riches votent X" ne signifie pas "les personnes riches votent X".
			On compare des moyennes communales, pas des comportements individuels.
		</div>
	</section>

	<!-- 2. DONNÉES -->
	<section>
		<h2>Sources de données</h2>
		<p>Toutes les données sont publiques et téléchargeables.</p>

		<div class="data-grid">
			<div class="data-card">
				<h3>Élections</h3>
				<ul>
					<li>Municipales 2026 (T1, T2)</li>
					<li>Européennes 2024</li>
					<li>Législatives 2024, 2022</li>
					<li>Présidentielles 2022 (T1), 2017 (T1)</li>
					<li>Régionales, Départementales 2021</li>
					<li>Municipales 2020 (T1, T2)</li>
				</ul>
				<p class="source">Source : data.gouv.fr — Ministère de l'Intérieur</p>
			</div>

			<div class="data-card">
				<h3>Socio-économique</h3>
				<ul>
					<li><strong>Revenus</strong> — Filosofi 2021 (revenu médian, taux de pauvreté)</li>
					<li><strong>Emploi</strong> — RP + IC 2021 (chômage, CSP, temps partiel)</li>
					<li><strong>Éducation</strong> — RP 2021 (diplômes, IPS scolaire)</li>
					<li><strong>Logement</strong> — RP + IC 2021 (propriété, HLM, vacance, loyers)</li>
					<li><strong>Territoire</strong> — Population 2022, densité, mobilité résidentielle</li>
					<li><strong>Vie locale</strong> — Associations (RNA), BPE, DVF, fibre</li>
					<li><strong>Sécurité</strong> — Délinquance par catégorie (SSMSI)</li>
					<li><strong>Santé</strong> — Accessibilité médecins (APL)</li>
				</ul>
				<p class="source">Source : INSEE (RP, IC, Filosofi), data.gouv.fr, SSMSI</p>
			</div>

			<div class="data-card">
				<h3>Géographie</h3>
				<ul>
					<li>Contours communes — résolution 50m et 1000m</li>
					<li>Contours départements et régions — 50m</li>
					<li>Superficie calculée en projection Lambert-93</li>
				</ul>
				<p class="source">Source : AdminExpress COG (data.gouv.fr)</p>
			</div>
		</div>

		<div class="stats-row">
			<div class="stat">
				<span class="stat-value">34 965</span>
				<span class="stat-label">communes</span>
			</div>
			<div class="stat">
				<span class="stat-value">201</span>
				<span class="stat-label">variables</span>
			</div>
			<div class="stat">
				<span class="stat-value">11</span>
				<span class="stat-label">scrutins</span>
			</div>
			<div class="stat">
				<span class="stat-value">3M+</span>
				<span class="stat-label">points de données</span>
			</div>
		</div>
	</section>

	<!-- 3. FAMILLES POLITIQUES -->
	<section>
		<h2>Classification politique</h2>
		<p>
			Les candidats et listes sont regroupés en <strong>6 familles</strong> pour permettre
			la comparaison entre scrutins :
		</p>
		<div class="families">
			<span class="fam fam-gauche">gauche</span>
			<span class="fam fam-centre">centre</span>
			<span class="fam fam-droite">droite</span>
			<span class="fam fam-exd">extrême droite</span>
			<span class="fam fam-divers">sans étiquette</span>
			<span class="fam fam-divers">autres</span>
		</div>
		<p>
			Pour les <strong>présidentielles</strong>, l'attribution se fait par nom de candidat
			(Macron → centre, Mélenchon → gauche, Le Pen → extrême droite, etc.).
			Pour les <strong>scrutins de liste</strong>, elle se fait par nuance politique officielle
			du Ministère de l'Intérieur.
		</p>
		<p class="small">
			Cette classification est nécessairement simplificatrice. Un candidat "divers gauche"
			en milieu rural n'a pas le même profil qu'un candidat LFI en métropole.
			Les scores par famille sont des ordres de grandeur, pas des mesures exactes.
		</p>
	</section>

	<!-- 4. MÉTHODES STATISTIQUES -->
	<section>
		<h2>Méthodes statistiques</h2>

		<h3>Corrélations</h3>
		<p>
			Corrélations de <strong>Pearson</strong> (linéaire) et <strong>Spearman</strong> (rang)
			entre chaque variable socio-éco et chaque score électoral. Seules les paires avec
			n ≥ 1 000 communes sont retenues. La p-value est fournie pour chaque paire.
		</p>

		<h3>Régression multivariée</h3>
		<p>
			Régression <strong>OLS</strong> (moindres carrés ordinaires) via statsmodels.
			10 variables électorales cibles (scores par famille sur 3 scrutins + abstention),
			21 prédicteurs socio-éco. Filtrées aux communes de 200+ habitants.
			Sortie : coefficients β, erreurs standard, R², AIC/BIC.
		</p>
		<p>
			Les <strong>résidus standardisés</strong> mesurent l'écart entre le score observé
			et le score prédit par le modèle. Un résidu de +2σ signifie que la commune vote
			nettement plus pour cette famille que son profil socio-éco ne le prédirait.
			C'est la mesure centrale de "l'exception au stéréotype".
		</p>

		<h3>Z-scores départementaux</h3>
		<p>
			Pour chaque commune, on calcule z = (x − μ<sub>dept</sub>) / σ<sub>dept</sub>,
			pondéré par la population. Un z-score de +3 signifie que la commune est à 3 écarts-types
			au-dessus de la moyenne de son département sur cette variable.
			Seuil d'anomalie : |z| ≥ 3.0.
		</p>

		<h3>Clustering (ACP + K-Means)</h3>
		<p>
			<strong>ACP</strong> sur 18 variables socio-éco standardisées → 6 composantes principales.
			Puis <strong>K-Means</strong> (8 clusters, k-means++, graine 42).
			Les clusters sont étiquetés par heuristique : urbanité, revenus, CSP dominante
			(ex : "Métropole aisée cadres", "Rural modeste agricole").
		</p>
	</section>

	<!-- 5. ARCHITECTURE -->
	<section>
		<h2>Architecture technique</h2>
		<p>
			Le pipeline est 100% Python. La base de données est <strong>DuckDB</strong>
			avec un modèle Entity-Attribute-Value (EAV) : ajouter une variable ne modifie
			jamais le schéma SQL.
		</p>
		<p>
			Le front-end est un site <strong>SvelteKit statique</strong>.
			Les données sont exportées en Parquet et chargées dans <strong>DuckDB-WASM</strong>
			directement dans le navigateur — aucun serveur backend, toutes les requêtes SQL
			tournent côté client.
		</p>
		<p>
			La carte utilise <strong>Maplibre GL</strong> avec 35 000 polygones communaux
			colorés en choroplèthe. Les contours sont simplifiés à 1000m pour la vue France
			entière, 50m pour le zoom.
		</p>
		<div class="pipeline">
			<span class="step">sources.yaml</span>
			<span class="arrow">→</span>
			<span class="step">download</span>
			<span class="arrow">→</span>
			<span class="step">transform</span>
			<span class="arrow">→</span>
			<span class="step">load</span>
			<span class="arrow">→</span>
			<span class="step">analyze</span>
			<span class="arrow">→</span>
			<span class="step">export .parquet</span>
			<span class="arrow">→</span>
			<span class="step">DuckDB-WASM</span>
		</div>
	</section>

	<!-- 6. LIMITES -->
	<section>
		<h2>Limites</h2>
		<ul class="limits">
			<li>
				<strong>Ecological fallacy</strong> — Corrélation territoriale ≠ causalité individuelle.
				On observe des agrégats communaux, pas des électeurs.
			</li>
			<li>
				<strong>Classification politique</strong> — Le regroupement en 6 familles écrase
				la diversité (ex : gauche radicale vs sociale-démocratie). Les nuances Intérieur
				sont parfois contestables.
			</li>
			<li>
				<strong>Petites communes</strong> — Sous 200 habitants, les variables sont
				très volatiles et les modèles peu fiables. Les régressions filtrent à 200+ hab.
			</li>
			<li>
				<strong>Temporalité</strong> — Les données socio-éco (2021-2022) et électorales
				(2017-2026) ne sont pas synchrones. Les profils communaux évoluent.
			</li>
			<li>
				<strong>DOM-TOM</strong> — Couverture variable selon les sources INSEE.
				Certaines variables manquent pour l'outre-mer.
			</li>
			<li>
				<strong>Secret statistique</strong> — L'INSEE masque les données des communes
				les plus petites. Certains indicateurs ont des trous.
			</li>
			<li>
				<strong>Causalité</strong> — VoteSocio montre des corrélations et des écarts,
				pas des mécanismes causaux. "Pourquoi" reste une question ouverte.
			</li>
		</ul>
	</section>

	<!-- 7. CODE -->
	<section>
		<h2>Code source</h2>
		<p>
			Tout le code est ouvert :
			<a href="https://github.com/bmatge/communes-elections-correlation" target="_blank" rel="noopener">
				github.com/bmatge/communes-elections-correlation
			</a>
		</p>
		<p class="small">
			Pipeline Python · DuckDB · SvelteKit · Maplibre GL · DuckDB-WASM ·
			scikit-learn · statsmodels · pandas
		</p>
	</section>
</article>

<style>
	.methode {
		max-width: 720px;
	}

	.page-header {
		margin-bottom: var(--spacing-2xl);
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
		font-size: 3rem;
		font-weight: 400;
		font-style: italic;
		line-height: 1.1;
		margin-bottom: var(--spacing-md);
	}

	.intro {
		font-size: 1.05rem;
		color: var(--color-text-muted);
		line-height: 1.6;
	}

	section {
		margin-bottom: var(--spacing-2xl);
	}

	h2 {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--color-accent);
		margin-bottom: var(--spacing-md);
		padding-bottom: var(--spacing-xs);
		border-bottom: 1px solid var(--color-border);
	}

	h3 {
		font-family: var(--font-sans);
		font-size: 0.95rem;
		font-weight: 700;
		margin-top: var(--spacing-lg);
		margin-bottom: var(--spacing-sm);
	}

	p {
		font-size: 0.88rem;
		color: var(--color-text-muted);
		line-height: 1.65;
		margin-bottom: var(--spacing-sm);
	}

	p.small {
		font-size: 0.75rem;
		color: var(--color-text-dim);
	}

	a {
		color: var(--color-accent);
		text-decoration: underline;
		text-underline-offset: 2px;
	}

	ul {
		padding-left: 1.2rem;
		margin-bottom: var(--spacing-md);
	}

	li {
		font-size: 0.85rem;
		color: var(--color-text-muted);
		line-height: 1.5;
		margin-bottom: 6px;
	}

	.callout {
		background: var(--color-surface);
		border-left: 3px solid var(--color-accent);
		padding: 12px 16px;
		border-radius: 0 6px 6px 0;
		font-size: 0.82rem;
		color: var(--color-text-muted);
		line-height: 1.6;
		margin: var(--spacing-md) 0;
	}

	.callout strong {
		color: var(--color-text);
	}

	/* Data grid */
	.data-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
		gap: var(--spacing-md);
		margin: var(--spacing-md) 0;
	}

	.data-card {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 16px;
	}

	.data-card h3 {
		font-family: var(--font-sans);
		font-size: 0.85rem;
		font-weight: 700;
		color: var(--color-text);
		margin-top: 0;
		margin-bottom: var(--spacing-sm);
	}

	.data-card ul {
		padding-left: 1rem;
		margin-bottom: var(--spacing-sm);
	}

	.data-card li {
		font-size: 0.75rem;
		margin-bottom: 3px;
	}

	.source {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--color-text-dim);
		margin: 0;
	}

	/* Stats row */
	.stats-row {
		display: flex;
		gap: var(--spacing-lg);
		margin: var(--spacing-lg) 0;
		padding: var(--spacing-md) 0;
		border-top: 1px solid var(--color-border);
		border-bottom: 1px solid var(--color-border);
	}

	.stat {
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.stat-value {
		font-family: var(--font-mono);
		font-size: 1.4rem;
		font-weight: 700;
		color: var(--color-text);
	}

	.stat-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--color-text-dim);
	}

	/* Families */
	.families {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin: var(--spacing-md) 0;
	}

	.fam {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		padding: 4px 12px;
		border-radius: 99px;
		border: 1px solid var(--color-border);
		color: var(--color-text-muted);
	}

	.fam-gauche { border-color: var(--color-gauche); color: var(--color-gauche); }
	.fam-centre { border-color: var(--color-centre); color: var(--color-centre); }
	.fam-droite { border-color: var(--color-droite); color: var(--color-droite); }
	.fam-exd { border-color: var(--color-exd); color: var(--color-exd); }

	/* Pipeline */
	.pipeline {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
		margin: var(--spacing-md) 0;
		font-family: var(--font-mono);
		font-size: 0.7rem;
	}

	.step {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 4px;
		padding: 4px 10px;
		color: var(--color-text);
	}

	.arrow {
		color: var(--color-text-dim);
	}

	/* Limits */
	.limits li {
		margin-bottom: var(--spacing-sm);
	}

	.limits strong {
		color: var(--color-text);
	}

	@media (max-width: 768px) {
		h1 { font-size: 2rem; }
		.stats-row { flex-wrap: wrap; }
		.pipeline { font-size: 0.6rem; }
	}
</style>
