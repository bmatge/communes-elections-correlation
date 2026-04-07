<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import '../app.css';

	let { children } = $props();
</script>

<svelte:head>
	<title>VoteSocio — Municipales 2026 × Socio-éco</title>
</svelte:head>

<div class="app">
	<Header />

	<main class="container">
		{@render children()}
	</main>

	<Footer />
</div>

<style>
	.app {
		display: flex;
		flex-direction: column;
		min-height: 100dvh;
	}

	main {
		flex: 1;
		min-height: 0;
		padding-top: var(--spacing-xl);
		padding-bottom: var(--spacing-xl);
	}
</style>
