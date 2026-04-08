import * as duckdb from '@duckdb/duckdb-wasm';

const PARQUET_FILES = [
	'commune_data.parquet',
	'variables_meta.parquet',
	'communes.parquet',
	'geo_communes.parquet',
	'geo_communes_lowres.parquet',
	'geo_departements.parquet',
	'geo_regions.parquet',
	// Tables d'analyse
	'correlation_matrix.parquet',
	'commune_zscores.parquet',
	'regression_results.parquet',
	'commune_residuals.parquet',
	'commune_clusters.parquet',
	'cluster_profiles.parquet',
	'pca_loadings.parquet',
	'regression_scaler.parquet',
	'decalage_local_national.parquet'
];

// Singleton promises to avoid race conditions
let initPromise: Promise<duckdb.AsyncDuckDB> | null = null;
let connPromise: Promise<duckdb.AsyncDuckDBConnection> | null = null;
const loadedFiles = new Set<string>();

export function initDB(): Promise<duckdb.AsyncDuckDB> {
	if (initPromise) return initPromise;

	initPromise = (async () => {
		const DUCKDB_BUNDLES = await duckdb.selectBundle({
			mvp: {
				mainModule: new URL('@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm', import.meta.url).href,
				mainWorker: new URL(
					'@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js',
					import.meta.url
				).href
			},
			eh: {
				mainModule: new URL('@duckdb/duckdb-wasm/dist/duckdb-eh.wasm', import.meta.url).href,
				mainWorker: new URL(
					'@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js',
					import.meta.url
				).href
			}
		});

		const logger = new duckdb.ConsoleLogger();
		const worker = new Worker(DUCKDB_BUNDLES.mainWorker!);
		const db = new duckdb.AsyncDuckDB(logger, worker);
		await db.instantiate(DUCKDB_BUNDLES.mainModule);

		// Load parquet files in parallel
		await Promise.all(
			PARQUET_FILES.map(async (file) => {
				const url = `${import.meta.env.BASE_URL}data/${file}`;
				try {
					const resp = await fetch(url);
					if (!resp.ok) return;
					const buffer = await resp.arrayBuffer();
					await db.registerFileBuffer(file, new Uint8Array(buffer));
					loadedFiles.add(file);
				} catch {
					// File not available — skip
				}
			})
		);

		console.log(`[DuckDB] ${loadedFiles.size}/${PARQUET_FILES.length} fichiers chargés`);
		return db;
	})();

	return initPromise;
}

export function getConnection(): Promise<duckdb.AsyncDuckDBConnection> {
	if (connPromise) return connPromise;

	connPromise = (async () => {
		const db = await initDB();
		const conn = await db.connect();

		// Disable autoloading extensions from the network
		await conn.query("SET autoinstall_known_extensions=false");
		await conn.query("SET autoload_known_extensions=false");

		// Create views only for files that were actually loaded
		for (const file of loadedFiles) {
			const viewName = file.replace('.parquet', '');
			await conn.query(`CREATE VIEW IF NOT EXISTS ${viewName} AS SELECT * FROM '${file}'`);
		}

		return conn;
	})();

	return connPromise;
}

export async function query<T = Record<string, unknown>>(sql: string): Promise<T[]> {
	const c = await getConnection();
	const result = await c.query(sql);
	return result.toArray().map((row) => row.toJSON() as T);
}

export async function queryOne<T = Record<string, unknown>>(sql: string): Promise<T | null> {
	const rows = await query<T>(sql);
	return rows[0] ?? null;
}
