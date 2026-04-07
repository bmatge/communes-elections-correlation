<script lang="ts">
	import { page } from '$app/state';
	import CommuneSearch from '$lib/components/CommuneSearch.svelte';
	import CommuneProfile from '$lib/components/CommuneProfile.svelte';

	let code = $derived(page.url.searchParams.get('code'));
</script>

<svelte:head>
	<title>{code ? 'Fiche commune' : 'Communes'} — VoteSocio</title>
</svelte:head>

<div class="commune-page">
	<div class="search-area">
		<CommuneSearch />
	</div>

	{#if code}
		<CommuneProfile {code} />
	{:else}
		<div class="empty-state">
			<p class="big">Tapez un nom de commune</p>
			<p class="sub">ou cliquez sur la carte pour voir le profil complet.</p>
		</div>
	{/if}
</div>

<style>
	.commune-page {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xl);
	}

	.search-area {
		display: flex;
		justify-content: center;
	}

	.empty-state {
		text-align: center;
		padding: var(--spacing-2xl) 0;
	}

	.big {
		font-family: var(--font-display);
		font-size: 1.5rem;
		color: var(--color-text-muted);
	}

	.sub {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--color-text-dim);
		margin-top: var(--spacing-xs);
	}
</style>
