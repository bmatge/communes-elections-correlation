<script lang="ts">
	import { page } from '$app/state';

	const nav = [
		{ href: '/carte', label: 'Carte' },
		{ href: '/commune', label: 'Communes' },
		{ href: '/simulateur', label: 'Simulateur' }
	];
</script>

<header>
	<div class="header-inner">
		<a href="/" class="logo">
			<span class="logo-mark">VS</span>
			<span class="logo-text">VoteSocio</span>
		</a>

		<nav>
			{#each nav as { href, label }}
				<a {href} class:active={page.url.pathname === href}>
					{label}
				</a>
			{/each}
		</nav>

		<span class="badge">beta</span>
	</div>
</header>

<style>
	header {
		border-bottom: 1px solid var(--color-border);
		backdrop-filter: blur(12px);
		background: rgba(12, 12, 15, 0.85);
		position: sticky;
		top: 0;
		z-index: 100;
	}

	.header-inner {
		max-width: var(--max-width);
		margin: 0 auto;
		padding: 0 var(--spacing-md);
		height: 52px;
		display: flex;
		align-items: center;
		gap: var(--spacing-lg);
	}

	.logo {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		text-decoration: none;
		color: var(--color-text);
	}

	.logo-mark {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 700;
		letter-spacing: 0.05em;
		background: var(--color-accent);
		color: var(--color-accent-text);
		padding: 2px 6px;
		border-radius: 3px;
	}

	.logo-text {
		font-family: var(--font-sans);
		font-weight: 700;
		font-size: 0.9rem;
		letter-spacing: -0.02em;
	}

	nav {
		display: flex;
		gap: 2px;
		margin-left: auto;
	}

	nav a {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 400;
		letter-spacing: 0.03em;
		text-transform: uppercase;
		color: var(--color-text-muted);
		padding: 6px 12px;
		border-radius: 4px;
		transition: color 0.12s, background 0.12s;
		text-decoration: none;
	}

	nav a:hover {
		color: var(--color-text);
		background: var(--color-surface-raised);
	}

	nav a.active {
		color: var(--color-accent);
		background: var(--color-surface-raised);
	}

	.badge {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--color-text-dim);
		border: 1px solid var(--color-border);
		padding: 2px 8px;
		border-radius: 99px;
	}
</style>
