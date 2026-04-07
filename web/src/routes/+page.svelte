<section class="hero">
	<div class="hero-left">
		<p class="kicker">Municipales 2026 × Données socio-économiques</p>
		<h1>
			<span class="line">Qui vote quoi,</span>
			<span class="line accent">et pourquoi&thinsp;?</span>
		</h1>
		<p class="lead">
			35&thinsp;000 communes. 120 variables. Revenus, diplômes, logement, emploi…
			croisés avec les résultats électoraux. Explorez les stéréotypes —
			<em>et leurs exceptions.</em>
		</p>
	</div>

	<aside class="kpis">
		<div class="stat">
			<span class="stat-value">35k</span>
			<span class="stat-label">communes</span>
		</div>
		<div class="stat">
			<span class="stat-value">120+</span>
			<span class="stat-label">variables</span>
		</div>
		<div class="stat">
			<span class="stat-value">10</span>
			<span class="stat-label">catégories</span>
		</div>
		<div class="stat">
			<span class="stat-value">1.8M</span>
			<span class="stat-label">données</span>
		</div>
	</aside>
</section>

<section class="cards">
	<a href="/carte" class="card">
		<div class="card-number">01</div>
		<h2>Carte</h2>
		<p>
			Choroplèthe interactive. Choisissez une variable, voyez la France se colorer.
			Zoomez. Comparez.
		</p>
		<span class="card-cta">Explorer &rarr;</span>
	</a>

	<a href="/commune" class="card">
		<div class="card-number">02</div>
		<h2>Fiche commune</h2>
		<p>
			Le portrait-robot d'une commune. Votes, revenus, âge, diplômes —
			tout sur une page.
		</p>
		<span class="card-cta">Chercher &rarr;</span>
	</a>

	<a href="/simulateur" class="card">
		<div class="card-number">03</div>
		<h2>Simulateur</h2>
		<p>
			Bougez les curseurs socio-éco. Le modèle prédit le profil de vote.
			Cassez les clichés.
		</p>
		<span class="card-cta">Jouer &rarr;</span>
	</a>
</section>


<style>
	/* Hero */
	.hero {
		display: flex;
		justify-content: space-between;
		align-items: start;
		gap: var(--spacing-xl);
		padding: var(--spacing-2xl) 0 var(--spacing-xl);
	}

	.hero-left {
		flex: 1;
		min-width: 0;
	}

	.kicker {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--color-accent);
		margin-bottom: var(--spacing-md);
	}

	h1 {
		font-family: var(--font-display);
		font-weight: 400;
		font-size: clamp(2.5rem, 7vw, 5rem);
		line-height: 1.05;
		letter-spacing: -0.03em;
	}

	.line {
		display: block;
	}

	.accent {
		font-style: italic;
		color: var(--color-accent);
	}

	.lead {
		margin-top: var(--spacing-lg);
		font-size: 1.1rem;
		line-height: 1.65;
		color: var(--color-text-muted);
		max-width: 540px;
	}

	.lead em {
		color: var(--color-text);
		font-style: normal;
		font-weight: 500;
	}

	/* KPIs */
	.kpis {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1px;
		background: var(--color-border);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		overflow: hidden;
		flex-shrink: 0;
		margin-top: 2.8rem;
	}

	.stat {
		background: var(--color-surface);
		padding: var(--spacing-md) var(--spacing-lg);
		text-align: center;
	}

	.stat-value {
		display: block;
		font-family: var(--font-mono);
		font-size: 1.35rem;
		font-weight: 700;
		color: var(--color-text);
		line-height: 1.2;
	}

	.stat-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--color-text-dim);
	}

	/* Cards */
	.cards {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 1px;
		background: var(--color-border);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		overflow: hidden;
		margin-top: var(--spacing-xl);
	}

	.card {
		display: flex;
		flex-direction: column;
		background: var(--color-surface);
		padding: var(--spacing-lg);
		text-decoration: none;
		color: var(--color-text);
		transition: background 0.2s;
	}

	.card:hover {
		background: var(--color-surface-raised);
		text-decoration: none;
	}

	.card-number {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--color-text-dim);
		margin-bottom: var(--spacing-lg);
	}

	.card h2 {
		font-family: var(--font-display);
		font-size: 1.5rem;
		font-weight: 400;
		margin-bottom: var(--spacing-sm);
	}

	.card p {
		font-size: 0.85rem;
		color: var(--color-text-muted);
		line-height: 1.6;
		flex: 1;
	}

	.card-cta {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--color-accent);
		margin-top: var(--spacing-lg);
		transition: letter-spacing 0.2s;
	}

	.card:hover .card-cta {
		letter-spacing: 0.05em;
	}

	/* Responsive */
	@media (max-width: 768px) {
		.hero {
			flex-direction: column;
		}

		.kpis {
			width: 100%;
			margin-top: 0;
		}

		.cards {
			grid-template-columns: 1fr;
		}
	}
</style>
