<script lang="ts">
	import { query } from '$lib/db';

	let { value = $bindable('revenu_median') }: { value?: string } = $props();

	type Variable = { variable_id: string; name: string; category: string };

	let variables = $state<Variable[]>([]);
	let grouped = $derived(groupByCategory(variables));

	const CATEGORY_LABELS: Record<string, string> = {
		revenus: 'Revenus',
		emploi: 'Emploi',
		logement: 'Logement',
		education: 'Éducation',
		territoire: 'Territoire',
		securite: 'Sécurité',
		sante: 'Santé',
		vie_locale: 'Vie locale',
		transport: 'Transport',
		electoral: 'Électoral'
	};

	const CATEGORY_ORDER = Object.keys(CATEGORY_LABELS);

	function groupByCategory(vars: Variable[]): [string, Variable[]][] {
		const map = new Map<string, Variable[]>();
		for (const v of vars) {
			const arr = map.get(v.category) || [];
			arr.push(v);
			map.set(v.category, arr);
		}
		return CATEGORY_ORDER.filter((c) => map.has(c)).map((c) => [c, map.get(c)!]);
	}

	$effect(() => {
		query<Variable>(
			"SELECT variable_id, name, category FROM variables_meta WHERE type = 'numeric' ORDER BY category, name"
		).then((rows) => {
			variables = rows;
		});
	});
</script>

<div class="selector">
	<label class="label" for="var-select">Variable</label>
	<select id="var-select" bind:value>
		{#each grouped as [cat, vars]}
			<optgroup label={CATEGORY_LABELS[cat] || cat}>
				{#each vars as v}
					<option value={v.variable_id}>{v.name}</option>
				{/each}
			</optgroup>
		{/each}
	</select>
</div>

<style>
	.selector {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.label {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--color-text-dim);
	}

	select {
		appearance: none;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 6px;
		color: var(--color-text);
		font-family: var(--font-sans);
		font-size: 0.85rem;
		padding: 8px 12px;
		cursor: pointer;
		width: 100%;
		max-width: 300px;
		transition: border-color 0.15s;
		background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%2372728a' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
		background-repeat: no-repeat;
		background-position: right 10px center;
		padding-right: 30px;
	}

	select:focus {
		outline: none;
		border-color: var(--color-accent);
	}

	select optgroup {
		font-weight: 700;
		color: var(--color-text-muted);
	}

	select option {
		background: var(--color-surface);
		color: var(--color-text);
		padding: 4px;
	}
</style>
