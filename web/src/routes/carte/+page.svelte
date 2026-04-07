<script lang="ts">
	import Map from '$lib/components/Map.svelte';
	import VariableSelector from '$lib/components/VariableSelector.svelte';
	import { goto } from '$app/navigation';

	let variableId = $state('revenu_median');

	function handleCommuneClick(code: string) {
		goto(`/commune?code=${code}`);
	}
</script>

<svelte:head>
	<title>Carte — VoteSocio</title>
</svelte:head>

<div class="carte-page">
	<aside class="sidebar">
		<h1>Carte</h1>
		<p class="desc">Choisissez une variable, la France se colore.</p>
		<VariableSelector bind:value={variableId} />
		<p class="hint">Cliquez sur une commune pour voir sa fiche.</p>
	</aside>
	<div class="map-area">
		<Map bind:variableId onCommuneClick={handleCommuneClick} />
	</div>
</div>

<style>
	.carte-page {
		display: flex;
		gap: var(--spacing-lg);
		height: calc(100dvh - 52px - var(--spacing-xl) * 2);
		min-height: 500px;
	}

	.sidebar {
		width: 280px;
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	h1 {
		font-family: var(--font-display);
		font-size: 1.75rem;
		font-weight: 400;
	}

	.desc {
		font-size: 0.85rem;
		color: var(--color-text-muted);
		line-height: 1.5;
	}

	.hint {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--color-text-dim);
		margin-top: auto;
	}

	.map-area {
		flex: 1;
		min-width: 0;
	}

	@media (max-width: 768px) {
		.carte-page {
			flex-direction: column;
			height: auto;
		}

		.sidebar {
			width: 100%;
		}

		.map-area {
			height: 60vh;
		}
	}
</style>
