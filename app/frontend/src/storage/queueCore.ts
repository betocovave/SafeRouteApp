import type { PendingReport, ReportResult } from '../api/types';

export async function flushReports(items: PendingReport[], send: (report: PendingReport) => Promise<ReportResult>, photo: (id: string, uri: string) => Promise<unknown>, checkpoint: (remaining: PendingReport[]) => Promise<void>) {
  const remaining = [...items];
  for (const item of [...remaining]) {
    try {
      if (!item.report_id) {
        const result = await send(item);
        item.report_id = result.report_id;
        await checkpoint(remaining);
      }
      if (item.local_photo) await photo(item.report_id, item.local_photo);
      remaining.splice(remaining.indexOf(item), 1);
    } catch (error) {
      item.error = error instanceof Error ? error.message : 'No se pudo enviar el reporte.';
    }
    await checkpoint(remaining);
  }
  return remaining;
}
