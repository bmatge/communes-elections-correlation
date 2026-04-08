<script lang="ts">
	import { page } from '$app/state';
	import { onMount } from 'svelte';

	const nav = [
		{ href: '/carte', label: 'Carte' },
		{ href: '/commune', label: 'Communes' },
		{ href: '/surprises', label: 'Surprises' },
		{ href: '/simulateur', label: 'Simulateur' },
		{ href: '/methode', label: 'Méthode' }
	];

	let dark = $state(true);

	onMount(() => {
		const saved = localStorage.getItem('theme');
		if (saved) {
			dark = saved === 'dark';
		} else {
			dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
		}
		applyTheme();
	});

	function toggleTheme() {
		dark = !dark;
		applyTheme();
		localStorage.setItem('theme', dark ? 'dark' : 'light');
	}

	function applyTheme() {
		document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
	}
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

		<button class="theme-toggle" onclick={toggleTheme} title={dark ? 'Mode clair' : 'Mode sombre'}>
			{#if dark}
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
			{:else}
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
			{/if}
		</button>

		<span class="badge">beta</span>
	</div>
</header>

<style>
	header {
		border-bottom: 1px solid var(--color-border);
		backdrop-filter: blur(12px);
		background: color-mix(in srgb, var(--color-bg) 85%, transparent);
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

	.theme-toggle {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		background: none;
		border: 1px solid var(--color-border);
		border-radius: 6px;
		color: var(--color-text-muted);
		cursor: pointer;
		transition: color 0.15s, border-color 0.15s;
		flex-shrink: 0;
	}

	.theme-toggle:hover {
		color: var(--color-accent);
		border-color: var(--color-accent);
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
