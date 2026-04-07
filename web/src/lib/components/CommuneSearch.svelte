<script lang="ts">
	import { query } from '$lib/db';
	import { goto } from '$app/navigation';

	type Commune = { code_commune: string; libelle: string; code_departement: string; population: number };

	let search = $state('');
	let results = $state<Commune[]>([]);
	let showResults = $state(false);
	let selectedIdx = $state(-1);
	let debounceTimer: ReturnType<typeof setTimeout>;

	function handleInput() {
		selectedIdx = -1;
		clearTimeout(debounceTimer);
		if (search.length < 2) {
			results = [];
			showResults = false;
			return;
		}
		debounceTimer = setTimeout(doSearch, 150);
	}

	async function doSearch() {
		const term = search.trim();
		if (term.length < 2) return;

		// Search by name or postal code
		const isCode = /^\d+$/.test(term);
		const sql = isCode
			? `SELECT code_commune, libelle, code_departement, population
			   FROM communes
			   WHERE code_commune LIKE '${term}%'
			   ORDER BY population DESC NULLS LAST
			   LIMIT 12`
			: `SELECT code_commune, libelle, code_departement, population
			   FROM communes
			   WHERE LOWER(libelle) LIKE '%${term.toLowerCase()}%'
			   ORDER BY population DESC NULLS LAST
			   LIMIT 12`;

		results = await query<Commune>(sql);
		showResults = results.length > 0;
	}

	function select(commune: Commune) {
		search = commune.libelle;
		showResults = false;
		goto(`/commune?code=${commune.code_commune}`);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (!showResults) return;
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			selectedIdx = Math.min(selectedIdx + 1, results.length - 1);
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			selectedIdx = Math.max(selectedIdx - 1, 0);
		} else if (e.key === 'Enter' && selectedIdx >= 0) {
			e.preventDefault();
			select(results[selectedIdx]);
		} else if (e.key === 'Escape') {
			showResults = false;
		}
	}

	function formatPop(n: number | null): string {
		if (!n) return '';
		return n.toLocaleString('fr-FR') + ' hab.';
	}
</script>

<div class="search-wrapper">
	<input
		type="text"
		bind:value={search}
		oninput={handleInput}
		onkeydown={handleKeydown}
		onfocus={() => results.length > 0 && (showResults = true)}
		onblur={() => setTimeout(() => (showResults = false), 200)}
		placeholder="Rechercher une commune…"
		autocomplete="off"
		spellcheck="false"
	/>

	{#if showResults}
		<ul class="results">
			{#each results as commune, i}
				<li class:selected={i === selectedIdx}>
					<button type="button" onmousedown={() => select(commune)}>
						<span class="commune-name">{commune.libelle}</span>
						<span class="commune-meta">
							{commune.code_departement} · {formatPop(commune.population)}
						</span>
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.search-wrapper {
		position: relative;
		width: 100%;
		max-width: 480px;
	}

	input {
		width: 100%;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		color: var(--color-text);
		font-family: var(--font-sans);
		font-size: 1rem;
		padding: 12px 16px;
		transition: border-color 0.15s;
	}

	input::placeholder {
		color: var(--color-text-dim);
	}

	input:focus {
		outline: none;
		border-color: var(--color-accent);
	}

	.results {
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
		margin-top: 4px;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		overflow: hidden;
		list-style: none;
		z-index: 50;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
	}

	.results li button {
		display: flex;
		justify-content: space-between;
		align-items: center;
		width: 100%;
		padding: 10px 16px;
		background: none;
		border: none;
		color: var(--color-text);
		font-family: var(--font-sans);
		font-size: 0.9rem;
		cursor: pointer;
		text-align: left;
		transition: background 0.1s;
	}

	.results li button:hover,
	.results li.selected button {
		background: var(--color-surface-raised);
	}

	.commune-name {
		font-weight: 500;
	}

	.commune-meta {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--color-text-muted);
	}
</style>
