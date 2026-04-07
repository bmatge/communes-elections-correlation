<footer>
	<div class="footer-inner">
		<div class="footer-left">
			<span class="label">VoteSocio</span>
			<span class="sep">/</span>
			<span class="note">Municipales 2026 × données socio-éco</span>
		</div>

		<div class="footer-right">
			<span class="caveat">Corrélation ≠ causalité</span>
			<span class="sep">·</span>
			<a href="https://www.data.gouv.fr" target="_blank" rel="noopener">data.gouv.fr</a>
			<span class="sep">·</span>
			<a href="https://www.insee.fr" target="_blank" rel="noopener">INSEE</a>
		</div>
	</div>
</footer>

<style>
	footer {
		border-top: 1px solid var(--color-border);
		margin-top: auto;
	}

	.footer-inner {
		max-width: var(--max-width);
		margin: 0 auto;
		padding: var(--spacing-md);
		display: flex;
		justify-content: space-between;
		align-items: center;
		flex-wrap: wrap;
		gap: var(--spacing-sm);
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--color-text-dim);
	}

	.label {
		color: var(--color-text-muted);
		font-weight: 700;
	}

	.sep {
		opacity: 0.3;
	}

	.caveat {
		font-style: italic;
		color: var(--color-text-dim);
	}

	a {
		color: var(--color-text-dim);
		transition: color 0.12s;
	}

	a:hover {
		color: var(--color-accent);
	}
</style>
