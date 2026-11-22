import type { FlakyTest, Project, Statistics, TestRun } from './types'

interface ReportData {
  project: Project
  statistics: Statistics
  runs: TestRun[]
  flakyTests: FlakyTest[]
}

function escapeHtml(value: string) {
  return value.replace(/[&<>"']/g, (character) => {
    const entities: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    }
    return entities[character]
  })
}

function formattedDate(value: string) {
  return new Intl.DateTimeFormat('uk-UA', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function statusLabel(status: string) {
  if (status === 'passed') return 'Passed'
  if (status === 'failed') return 'Failed'
  if (status === 'skipped') return 'Skipped'
  return status
}

function createReportHtml(data: ReportData, printOnOpen: boolean) {
  const { project, statistics, runs, flakyTests } = data
  const runRows = runs.length
    ? runs.map((run) => `
      <tr>
        <td>${escapeHtml(formattedDate(run.created_at))}</td>
        <td>${escapeHtml(run.source_filename)}</td>
        <td>${escapeHtml(run.branch)}${run.build_number === null ? '' : ` · #${run.build_number}`}</td>
        <td>${run.total_tests}</td>
        <td>${run.passed_tests}</td>
        <td>${run.failed_tests}</td>
        <td>${run.skipped_tests}</td>
        <td>${run.pass_rate.toFixed(1)}%</td>
        <td>${escapeHtml(statusLabel(run.status))}</td>
      </tr>`).join('')
    : '<tr><td colspan="9">No test runs have been imported for this project.</td></tr>'
  const flakyRows = flakyTests.length
    ? flakyTests.map((test) => `
      <tr>
        <td>${escapeHtml(test.name)}</td>
        <td>${escapeHtml(test.classname || '—')}</td>
        <td>${test.total_runs}</td>
        <td>${test.failed_runs}</td>
        <td>${test.failure_rate.toFixed(1)}%</td>
      </tr>`).join('')
    : '<tr><td colspan="5">No flaky tests were found in the loaded results.</td></tr>'
  const printScript = printOnOpen
    ? '<script>window.addEventListener("load", () => window.print())</script>'
    : ''

  return `<!doctype html>
<html lang="uk">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Test report — ${escapeHtml(project.name)}</title>
  <style>
    :root { color-scheme: light; font-family: Arial, sans-serif; color: #242437; background: #fff; }
    body { max-width: 1100px; margin: 0 auto; padding: 36px; }
    header { display: flex; justify-content: space-between; align-items: start; gap: 24px; border-bottom: 2px solid #8839ef; padding-bottom: 20px; }
    h1 { margin: 0; font-size: 28px; }
    h2 { margin: 30px 0 12px; font-size: 18px; }
    p, small { color: #626276; }
    .meta { text-align: right; white-space: nowrap; }
    .metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 20px; }
    .metric { border: 1px solid #d9d9e5; padding: 14px; }
    .metric span { display: block; color: #626276; font-size: 12px; }
    .metric strong { display: block; margin-top: 7px; font-size: 23px; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th, td { border: 1px solid #d9d9e5; padding: 9px; text-align: left; vertical-align: top; }
    th { background: #f2effa; }
    .toolbar { display: flex; justify-content: flex-end; margin-bottom: 18px; }
    .toolbar button { border: 1px solid #8839ef; border-radius: 2px; padding: 9px 13px; color: #fff; background: #8839ef; font: inherit; cursor: pointer; }
    @media (max-width: 650px) { body { padding: 20px 14px; } header { display: block; } .meta { margin-top: 12px; text-align: left; } .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @page { size: landscape; margin: 14mm; }
    @media print { body { max-width: none; padding: 0; } .toolbar { display: none; } .table-wrap { overflow: visible; } th, td { padding: 6px; } }
  </style>
</head>
<body>
  <div class="toolbar"><button type="button" onclick="window.print()">Save as PDF</button></div>
  <header>
    <div><small>AutoTestReport Hub · automated test report</small><h1>${escapeHtml(project.name)}</h1><p>${escapeHtml(project.description || 'Automated test result summary.')}</p></div>
    <div class="meta"><strong>Generated</strong><br>${escapeHtml(formattedDate(new Date().toISOString()))}</div>
  </header>
  <section class="metrics" aria-label="Summary metrics">
    <div class="metric"><span>Runs</span><strong>${statistics.total_runs}</strong></div>
    <div class="metric"><span>Tests</span><strong>${statistics.total_tests}</strong></div>
    <div class="metric"><span>Average pass rate</span><strong>${statistics.average_pass_rate.toFixed(1)}%</strong></div>
    <div class="metric"><span>Flaky tests</span><strong>${flakyTests.length}</strong></div>
    <div class="metric"><span>Passed</span><strong>${statistics.passed_tests}</strong></div>
    <div class="metric"><span>Failed</span><strong>${statistics.failed_tests}</strong></div>
    <div class="metric"><span>Skipped</span><strong>${statistics.skipped_tests}</strong></div>
  </section>
  <section><h2>Recent imported runs</h2><div class="table-wrap"><table>
    <thead><tr><th>Date</th><th>File</th><th>Branch / build</th><th>Total</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Pass rate</th><th>Status</th></tr></thead>
    <tbody>${runRows}</tbody>
  </table></div><p><small>Showing up to ${runs.length} latest runs loaded by the interface.</small></p></section>
  <section><h2>Flaky tests</h2><div class="table-wrap"><table>
    <thead><tr><th>Test</th><th>Class</th><th>Runs</th><th>Failed runs</th><th>Failure rate</th></tr></thead>
    <tbody>${flakyRows}</tbody>
  </table></div></section>
  ${printScript}
</body>
</html>`
}

function safeFilename(projectName: string) {
  const normalized = projectName
    .normalize('NFKD')
    .replace(/[^\p{L}\p{N}]+/gu, '-')
    .replace(/^-|-$/g, '')
    .toLowerCase()
  return `${normalized || 'project'}-test-report`
}

export function downloadHtmlReport(data: ReportData) {
  const report = createReportHtml(data, false)
  const url = URL.createObjectURL(new Blob([report], { type: 'text/html;charset=utf-8' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${safeFilename(data.project.name)}.html`
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000)
}

export function openPrintReport(data: ReportData) {
  const report = createReportHtml(data, true)
  const url = URL.createObjectURL(new Blob([report], { type: 'text/html;charset=utf-8' }))
  const printWindow = window.open(url, '_blank')
  if (!printWindow) {
    URL.revokeObjectURL(url)
    return false
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  return true
}
