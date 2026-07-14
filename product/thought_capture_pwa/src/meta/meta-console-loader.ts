interface DocumentWriter {
  open(): void;
  write(html: string): void;
  close(): void;
}

interface LoadMetaConsoleDocumentOptions {
  consoleUrl: string;
  documentRef: DocumentWriter;
  fetchFn?: typeof fetch;
}

export async function loadMetaConsoleDocument({
  consoleUrl,
  documentRef,
  fetchFn = fetch,
}: LoadMetaConsoleDocumentOptions): Promise<void> {
  const response = await fetchFn(consoleUrl, {
    cache: "no-store",
    credentials: "same-origin",
    headers: { Accept: "text/html" },
  });

  if (!response.ok) {
    throw new Error(`Failed to load meta surface (${response.status})`);
  }

  const html = await response.text();
  documentRef.open();
  documentRef.write(html);
  documentRef.close();
}
