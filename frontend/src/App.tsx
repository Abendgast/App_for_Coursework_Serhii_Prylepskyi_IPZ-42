import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type FormEvent,
  type ReactNode,
} from 'react'
import { api } from './api'
import type {
  CreatedProject,
  FlakyTest,
  Project,
  Statistics,
  TestRun,
  TestRunDetails,
  User,
} from './types'
import { downloadHtmlReport, openPrintReport } from './report'
import './App.css'

type IconName =
  | 'activity'
  | 'alert'
  | 'arrow'
  | 'bars'
  | 'check'
  | 'chevron'
  | 'close'
  | 'cloud'
  | 'code'
  | 'dashboard'
  | 'edit'
  | 'file'
  | 'folder'
  | 'logout'
  | 'plus'
  | 'refresh'
  | 'search'
  | 'shield'
  | 'spark'
  | 'upload'
  | 'user'

const iconPaths: Record<IconName, string[]> = {
  activity: ['M22 12h-4l-3 9L9 3l-3 9H2'],
  alert: ['M12 9v4', 'M12 17h.01', 'M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z'],
  arrow: ['M7 17 17 7', 'M7 7h10v10'],
  bars: ['M3 3h18v18H3z', 'M9 3v18', 'M3 9h6', 'M3 15h6'],
  check: ['m5 12 4 4L19 6'],
  chevron: ['m9 18 6-6-6-6'],
  close: ['M18 6 6 18', 'm6 6 12 12'],
  cloud: ['M20 16.2A4.5 4.5 0 0 0 18.5 7H17A6 6 0 1 0 5 17h13'],
  code: ['m16 18 6-6-6-6', 'm8 6-6 6 6 6', 'm14 4-4 16'],
  dashboard: ['M3 3h8v8H3z', 'M13 3h8v5h-8z', 'M13 10h8v11h-8z', 'M3 13h8v8H3z'],
  edit: ['M12 20h9', 'M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z'],
  file: ['M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z', 'M14 2v6h6', 'M8 13h8', 'M8 17h8'],
  folder: ['M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'],
  logout: ['M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4', 'm16 17 5-5-5-5', 'M21 12H9'],
  plus: ['M12 5v14', 'M5 12h14'],
  refresh: ['M20 7v5h-5', 'M4 17v-5h5', 'M5.6 9a7 7 0 0 1 11.6-2L20 12', 'M4 12l2.8 5a7 7 0 0 0 11.6-2'],
  search: ['m21 21-4.3-4.3', 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z'],
  shield: ['M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z', 'm9 12 2 2 4-4'],
  spark: ['m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3Z', 'M19 14v4', 'M21 16h-4'],
  upload: ['M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4', 'm17 8-5-5-5 5', 'M12 3v12'],
  user: ['M20 21a8 8 0 0 0-16 0', 'M12 13a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z'],
}

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {iconPaths[name].map((path) => (
        <path d={path} key={path} />
      ))}
    </svg>
  )
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('en-US').format(value)
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en-US', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function shortDate(value: string) {
  return new Intl.DateTimeFormat('en-US', { day: 'numeric', month: 'short' }).format(
    new Date(value),
  )
}

function statusLabel(status: string) {
  if (status === 'passed') return 'Passed'
  if (status === 'failed') return 'Failed'
  if (status === 'skipped') return 'Skipped'
  return status
}

function initials(user: User) {
  return user.display_name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem('ath_access_token'))
  const [user, setUser] = useState<User | null>(null)
  const [verifiedToken, setVerifiedToken] = useState<string | null>(null)
  const [sessionError, setSessionError] = useState('')
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [authBusy, setAuthBusy] = useState(false)
  const [authError, setAuthError] = useState('')
  const [authNotice, setAuthNotice] = useState('')
  const [authEmail, setAuthEmail] = useState('')
  const [authName, setAuthName] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [projects, setProjects] = useState<Project[]>([])
  const [loadedProjectsToken, setLoadedProjectsToken] = useState('')
  const [selectedProjectId, setSelectedProjectId] = useState('')
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [runs, setRuns] = useState<TestRun[]>([])
  const [flakyTests, setFlakyTests] = useState<FlakyTest[]>([])
  const [loadedDataProjectId, setLoadedDataProjectId] = useState('')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [dataError, setDataError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [activePage, setActivePage] = useState<'overview' | 'runs' | 'flaky'>('overview')
  const [projectDialog, setProjectDialog] = useState<
    { mode: 'create' } | { mode: 'edit'; project: Project } | null
  >(null)
  const [newProjectKey, setNewProjectKey] = useState('')
  const [selectedRun, setSelectedRun] = useState<TestRunDetails | null>(null)
  const [runLoading, setRunLoading] = useState(false)
  const [runError, setRunError] = useState('')
  const [actionBusy, setActionBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!token) {
      return
    }

    const controller = new AbortController()
    api
      .me(token, controller.signal)
      .then((currentUser) => {
        setUser(currentUser)
        setVerifiedToken(token)
      })
      .catch((error: Error) => {
        if (controller.signal.aborted) return
        if (error.message.includes('(401)') || error.message.includes('(403)')) {
          sessionStorage.removeItem('ath_access_token')
          setToken(null)
          setUser(null)
        } else {
          setSessionError(error.message)
        }
      })
    return () => controller.abort()
  }, [token])

  useEffect(() => {
    if (!token || !user) return
    const controller = new AbortController()
    api
      .projects(token, controller.signal)
      .then((items) => {
        setProjects(items)
        setSelectedProjectId((current) =>
          items.some((project) => project.id === current) ? current : (items[0]?.id ?? ''),
        )
      })
      .catch((error: Error) => {
        if (!controller.signal.aborted) setDataError(error.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadedProjectsToken(token)
      })
    return () => controller.abort()
  }, [token, user])

  useEffect(() => {
    if (!token || !selectedProjectId) return

    const controller = new AbortController()
    Promise.all([
      api.statistics(token, selectedProjectId, controller.signal),
      api.runs(token, selectedProjectId, controller.signal),
      api.flakyTests(token, selectedProjectId, controller.signal),
    ])
      .then(([nextStatistics, nextRuns, nextFlaky]) => {
        setStatistics(nextStatistics)
        setRuns(nextRuns.items)
        setFlakyTests(nextFlaky)
      })
      .catch((error: Error) => {
        if (!controller.signal.aborted) setDataError(error.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoadedDataProjectId(selectedProjectId)
          setIsRefreshing(false)
        }
      })
    return () => controller.abort()
  }, [token, selectedProjectId, refreshKey])

  async function handleAuthSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAuthBusy(true)
    setAuthError('')
    setAuthNotice('')
    setSessionError('')
    try {
      if (authMode === 'register') {
        await api.register({
          email: authEmail,
          display_name: authName,
          password: authPassword,
        })
        setAuthNotice('Account created. Sign in to continue.')
        setAuthMode('login')
        setAuthPassword('')
      } else {
        const result = await api.login({ email: authEmail, password: authPassword })
        sessionStorage.setItem('ath_access_token', result.access_token)
        setToken(result.access_token)
        setAuthPassword('')
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'The request could not be completed.')
    } finally {
      setAuthBusy(false)
    }
  }

  function signOut() {
    sessionStorage.removeItem('ath_access_token')
    setToken(null)
    setUser(null)
    setVerifiedToken(null)
    setProjects([])
    setLoadedProjectsToken('')
    setSelectedProjectId('')
    setStatistics(null)
    setRuns([])
    setFlakyTests([])
    setLoadedDataProjectId('')
    setIsRefreshing(false)
    setSessionError('')
    setAuthNotice('')
  }

  async function handleProjectSave(name: string, description: string) {
    if (!token) return
    setActionBusy(true)
    setDataError('')
    try {
      if (projectDialog?.mode === 'edit') {
        const updated = await api.updateProject(token, projectDialog.project.id, {
          name,
          description,
        })
        setProjects((current) =>
          current.map((project) => (project.id === updated.id ? updated : project)),
        )
        setNotice('Project updated.')
      } else {
        const created: CreatedProject = await api.createProject(token, { name, description })
        setProjects((current) => [...current, created])
        setSelectedProjectId(created.id)
        setNewProjectKey(created.api_key)
        setNotice('')
      }
      setProjectDialog(null)
    } catch (error) {
      setDataError(error instanceof Error ? error.message : 'The project could not be saved.')
      throw error
    } finally {
      setActionBusy(false)
    }
  }

  async function handleDeleteProject() {
    if (!token || !selectedProject) return
    if (!window.confirm(`Delete project “${selectedProject.name}” and all of its reports?`)) {
      return
    }
    setActionBusy(true)
    try {
      await api.deleteProject(token, selectedProject.id)
      const remaining = projects.filter((project) => project.id !== selectedProject.id)
      setProjects(remaining)
      setSelectedProjectId(remaining[0]?.id ?? '')
      setIsRefreshing(false)
      setNotice('Project deleted.')
    } catch (error) {
      setDataError(error instanceof Error ? error.message : 'The project could not be deleted.')
    } finally {
      setActionBusy(false)
    }
  }

  async function handleUpload(file?: File) {
    if (!file || !token || !selectedProjectId) return
    const extension = file.name.split('.').pop()?.toLowerCase()
    if (extension !== 'xml' && extension !== 'json') {
      setDataError('Choose a report in JUnit XML or JSON format.')
      return
    }
    setActionBusy(true)
    setDataError('')
    try {
      await api.upload(token, selectedProjectId, file)
      setProjects((current) =>
        current.map((project) =>
          project.id === selectedProjectId
            ? { ...project, runs_count: project.runs_count + 1 }
            : project,
        ),
      )
      setNotice(`Report “${file.name}” uploaded successfully.`)
      setIsRefreshing(true)
      setRefreshKey((value) => value + 1)
      if (fileInput.current) fileInput.current.value = ''
    } catch (error) {
      setDataError(error instanceof Error ? error.message : 'The report could not be uploaded.')
    } finally {
      setActionBusy(false)
    }
  }

  async function openRun(run: TestRun) {
    if (!token) return
    setSelectedRun(null)
    setRunError('')
    setRunLoading(true)
    try {
      setSelectedRun(await api.run(token, run.id))
    } catch (error) {
      setRunError(error instanceof Error ? error.message : 'The test run could not be loaded.')
    } finally {
      setRunLoading(false)
    }
  }

  async function copyProjectKey() {
    try {
      await navigator.clipboard.writeText(newProjectKey)
      setNotice('Project key copied to the clipboard.')
    } catch {
      setNotice('The key could not be copied. Select and copy it manually.')
    }
  }

  function refreshData() {
    setDataError('')
    setIsRefreshing(true)
    setRefreshKey((value) => value + 1)
  }

  function exportHtmlReport() {
    if (!selectedProject || !visibleStatistics) return
    downloadHtmlReport({
      project: selectedProject,
      statistics: visibleStatistics,
      runs: visibleRuns,
      flakyTests: visibleFlakyTests,
    })
    setNotice('HTML report generated from the loaded project data.')
  }

  function printReport() {
    if (!selectedProject || !visibleStatistics) return
    const opened = openPrintReport({
      project: selectedProject,
      statistics: visibleStatistics,
      runs: visibleRuns,
      flakyTests: visibleFlakyTests,
    })
    if (!opened) setDataError('Allow pop-ups to open the report for printing.')
  }

  const selectedProject = projects.find((project) => project.id === selectedProjectId) ?? null
  const sessionChecked = !token || verifiedToken === token
  const projectsLoading = Boolean(token && user && loadedProjectsToken !== token)
  const dataLoading = Boolean(selectedProjectId && loadedDataProjectId !== selectedProjectId)
  const visibleStatistics =
    selectedProjectId === loadedDataProjectId ? statistics : null
  const visibleRuns = selectedProjectId === loadedDataProjectId ? runs : []
  const visibleFlakyTests = selectedProjectId === loadedDataProjectId ? flakyTests : []
  const pageTitle =
    activePage === 'runs'
      ? 'Run history'
      : activePage === 'flaky'
        ? 'Flaky tests'
        : 'Project overview'

  if (sessionError) {
    return (
      <LoadingScreen
        label={sessionError}
        action={
          <button className="button button-primary" onClick={signOut}>
            Return to sign in
          </button>
        }
      />
    )
  }

  if (!sessionChecked) {
    return <LoadingScreen label="Verifying session…" />
  }

  if (!token || !user) {
    return (
      <AuthScreen
        mode={authMode}
        busy={authBusy}
        error={authError}
        notice={authNotice}
        email={authEmail}
        name={authName}
        password={authPassword}
        onModeChange={(mode) => {
          setAuthMode(mode)
          setAuthError('')
          setAuthNotice('')
        }}
        onEmailChange={setAuthEmail}
        onNameChange={setAuthName}
        onPasswordChange={setAuthPassword}
        onSubmit={handleAuthSubmit}
      />
    )
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button
          className="brand brand-button"
          aria-label="AutoTestReport Hub home"
          onClick={() => setActivePage('overview')}
        >
          <span className="brand-mark">
            <Icon name="activity" size={20} />
          </span>
          <span>
            <strong>AutoTest</strong>
            <small>REPORT HUB</small>
          </span>
        </button>

        <div className="sidebar-section-label">ANALYTICS</div>
        <nav className="side-nav" aria-label="Main navigation">
          <button
            className={activePage === 'overview' ? 'nav-item active' : 'nav-item'}
            aria-label="Overview"
            onClick={() => setActivePage('overview')}
          >
            <Icon name="dashboard" />
            <span>Overview</span>
          </button>
          <button
            className={activePage === 'runs' ? 'nav-item active' : 'nav-item'}
            aria-label="Runs"
            onClick={() => setActivePage('runs')}
          >
            <Icon name="activity" />
            <span>Runs</span>
            <span className="nav-count">{selectedProject?.runs_count ?? 0}</span>
          </button>
          <button
            className={activePage === 'flaky' ? 'nav-item active' : 'nav-item'}
            aria-label="Flaky tests"
            onClick={() => setActivePage('flaky')}
          >
            <Icon name="alert" />
            <span>Flaky tests</span>
          </button>
        </nav>

        <div className="sidebar-section-row">
          <span className="sidebar-section-label">PROJECTS</span>
          <button
            className="icon-button sidebar-add"
            title="Create project"
            aria-label="Create project"
            onClick={() => setProjectDialog({ mode: 'create' })}
          >
            <Icon name="plus" size={16} />
          </button>
        </div>
        <div className="project-nav">
          {projects.map((project) => (
            <button
              key={project.id}
              className={selectedProjectId === project.id ? 'project-nav-item selected' : 'project-nav-item'}
              aria-label={project.name}
              onClick={() => {
                setSelectedProjectId(project.id)
                setActivePage('overview')
                setDataError('')
              }}
            >
              <span className="project-color">{project.name.slice(0, 1).toUpperCase()}</span>
              <span className="project-nav-name">{project.name}</span>
              <span className="project-runs">{project.runs_count}</span>
            </button>
          ))}
          {projects.length === 0 && <p className="sidebar-empty">No projects yet</p>}
        </div>

        <div className="sidebar-bottom">
          <div className="profile-row">
            <span className="avatar">{initials(user)}</span>
            <span className="profile-copy">
              <strong>{user.display_name}</strong>
              <small>{user.email}</small>
            </span>
            <button
              className="icon-button logout-button"
              title="Sign out"
              aria-label="Sign out"
              onClick={signOut}
            >
              <Icon name="logout" size={17} />
            </button>
          </div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="breadcrumb">
            <span>Projects</span>
            <Icon name="chevron" size={14} />
            <strong>{selectedProject?.name ?? 'Workspace'}</strong>
          </div>
          <div className="topbar-actions">
            <button
              className="icon-button refresh-button"
              title="Refresh data"
              aria-label="Refresh data"
              onClick={refreshData}
              disabled={!selectedProjectId || dataLoading || isRefreshing}
            >
              <Icon name="refresh" size={17} />
            </button>
            {selectedProject && (
              <>
                <button
                  className="button button-secondary export-button"
                  onClick={exportHtmlReport}
                  disabled={!visibleStatistics || dataLoading}
                  title="Download HTML report"
                >
                  <Icon name="file" size={15} />
                  <span>HTML</span>
                </button>
                <button
                  className="button button-secondary export-button"
                  onClick={printReport}
                  disabled={!visibleStatistics || dataLoading}
                  title="Print or save the report as PDF"
                >
                  <Icon name="file" size={15} />
                  <span>PDF</span>
                </button>
              <button
                className="button button-primary upload-button"
                onClick={() => fileInput.current?.click()}
                disabled={actionBusy}
              >
                <Icon name="upload" size={16} />
                <span>Upload report</span>
              </button>
              </>
            )}
            <input
              ref={fileInput}
              className="visually-hidden"
              type="file"
              accept=".xml,.json,application/xml,application/json"
              onChange={(event) => void handleUpload(event.target.files?.[0])}
            />
          </div>
        </header>

        <div className="content-area">
          {notice && (
            <div className="notice-banner">
              <Icon name="check" size={17} />
              <span>{notice}</span>
              <button className="icon-button" aria-label="Dismiss" onClick={() => setNotice('')}>
                <Icon name="close" size={16} />
              </button>
            </div>
          )}
          {dataError && (
            <div className="error-banner" role="alert">
              <Icon name="alert" size={17} />
              <span>{dataError}</span>
              <button className="icon-button" aria-label="Dismiss" onClick={() => setDataError('')}>
                <Icon name="close" size={16} />
              </button>
            </div>
          )}
          {selectedProject ? (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow"><span className="eyebrow-dot" /> WORKSPACE / {selectedProject.name}</div>
                  <h1>{pageTitle}</h1>
                  <p>
                    {activePage === 'overview'
                      ? selectedProject.description || 'Monitor automated test quality and run history.'
                      : activePage === 'runs'
                        ? 'Review results from imported test reports.'
                        : 'Tests with different outcomes across runs.'}
                  </p>
                </div>
                <div className="heading-actions">
                  <button
                    className="button button-secondary"
                    onClick={() => setProjectDialog({ mode: 'edit', project: selectedProject })}
                  >
                    <Icon name="edit" size={15} />
                    Settings
                  </button>
                  <button
                    className="icon-button delete-project"
                    title="Delete project"
                    onClick={() => void handleDeleteProject()}
                    disabled={actionBusy}
                  >
                    <Icon name="close" size={17} />
                  </button>
                </div>
              </div>

              {activePage === 'overview' && (
                <Overview
                  statistics={visibleStatistics}
                  runs={visibleRuns}
                  flakyTests={visibleFlakyTests}
                  loading={dataLoading || isRefreshing}
                  onRunClick={(run) => void openRun(run)}
                  onSeeRuns={() => setActivePage('runs')}
                  onSeeFlaky={() => setActivePage('flaky')}
                  onCreateProject={() => setProjectDialog({ mode: 'create' })}
                  onUpload={() => fileInput.current?.click()}
                />
              )}
              {activePage === 'runs' && (
                <RunsPage
                  runs={visibleRuns}
                  loading={dataLoading || isRefreshing}
                  onRunClick={(run) => void openRun(run)}
                />
              )}
              {activePage === 'flaky' && (
                <FlakyPage tests={visibleFlakyTests} loading={dataLoading || isRefreshing} />
              )}
            </>
          ) : projectsLoading ? (
            <LoadingPanel />
          ) : (
            <EmptyProjects onCreate={() => setProjectDialog({ mode: 'create' })} />
          )}
          <footer className="page-footer">
            <span>AutoTestReport Hub</span>
            <span>Test quality, clearly reported</span>
          </footer>
        </div>
      </main>

      {projectDialog && (
        <ProjectDialog
          mode={projectDialog.mode}
          project={projectDialog.mode === 'edit' ? projectDialog.project : undefined}
          busy={actionBusy}
          onClose={() => setProjectDialog(null)}
          onSave={handleProjectSave}
        />
      )}
      {newProjectKey && (
        <Modal title="Project created" onClose={() => setNewProjectKey('')}>
          <div className="key-dialog">
            <div className="key-warning"><Icon name="shield" /><span>Save this key. It is shown only once.</span></div>
            <p>Use it to upload reports from CI/CD. Uploads in the web app use your account.</p>
            <label htmlFor="project-key">Project key</label>
            <div className="key-field">
              <code id="project-key">{newProjectKey}</code>
              <button className="button button-secondary" onClick={() => void copyProjectKey()}>Copy</button>
            </div>
            <button className="button button-primary full-button" onClick={() => setNewProjectKey('')}>Done</button>
          </div>
        </Modal>
      )}
      {(selectedRun || runLoading || runError) && (
        <RunDialog
          run={selectedRun}
          loading={runLoading}
          error={runError}
          onClose={() => {
            setSelectedRun(null)
            setRunError('')
          }}
        />
      )}
    </div>
  )
}

function LoadingScreen({ label, action }: { label: string; action?: ReactNode }) {
  return (
    <div className="loading-screen">
      <span className="brand-mark"><Icon name="activity" size={20} /></span>
      <div className="loader" />
      <p>{label}</p>
      {action}
    </div>
  )
}

function AuthScreen({
  mode,
  busy,
  error,
  notice,
  email,
  name,
  password,
  onModeChange,
  onEmailChange,
  onNameChange,
  onPasswordChange,
  onSubmit,
}: {
  mode: 'login' | 'register'
  busy: boolean
  error: string
  notice: string
  email: string
  name: string
  password: string
  onModeChange: (mode: 'login' | 'register') => void
  onEmailChange: (value: string) => void
  onNameChange: (value: string) => void
  onPasswordChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}) {
  return (
    <main className="auth-page">
      <header className="auth-brand brand">
        <span className="brand-mark"><Icon name="activity" size={20} /></span>
        <span><strong>AutoTest</strong><small>REPORT HUB</small></span>
      </header>
      <div className="auth-layout">
        <section className="auth-intro">
          <div className="auth-pill">AUTOMATED TEST REPORTING</div>
          <h1>Test results<br />in one place.</h1>
          <p>Collect automated test results, track quality over time, and find flaky tests from one workspace.</p>
        </section>
        <section className="auth-card">
          <div className="auth-card-heading">
            <span className="auth-card-icon"><Icon name={mode === 'login' ? 'user' : 'plus'} size={18} /></span>
            <div><h2>{mode === 'login' ? 'Welcome back' : 'Create an account'}</h2><p>{mode === 'login' ? 'Sign in to continue' : 'Start working with test reports'}</p></div>
          </div>
          <form className="auth-form" onSubmit={onSubmit}>
            {mode === 'register' && (
              <label className="field">
                <span>Name</span>
                <span className="input-wrap"><Icon name="user" size={17} /><input autoComplete="name" value={name} onChange={(event) => onNameChange(event.target.value)} placeholder="Your name" minLength={2} maxLength={120} required /></span>
              </label>
            )}
            <label className="field">
              <span>Email address</span>
              <span className="input-wrap"><Icon name="user" size={17} /><input type="email" autoComplete="email" value={email} onChange={(event) => onEmailChange(event.target.value)} placeholder="name@example.com" required /></span>
            </label>
            <label className="field">
              <span>Password</span>
              <span className="input-wrap"><Icon name="shield" size={17} /><input type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={(event) => onPasswordChange(event.target.value)} placeholder="At least 12 characters" minLength={mode === 'register' ? 12 : 1} maxLength={128} required /></span>
              {mode === 'register' && <small className="field-hint">Use at least 12 characters.</small>}
            </label>
            {error && <div className="auth-error" role="alert"><Icon name="alert" size={16} />{error}</div>}
            {notice && <div className="auth-notice"><Icon name="check" size={16} />{notice}</div>}
            <button className="button button-primary auth-submit" type="submit" disabled={busy}>
              {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
              {!busy && <Icon name="arrow" size={16} />}
            </button>
          </form>
          <div className="auth-switch">
            {mode === 'login' ? 'New here?' : 'Already have an account?'}
            <button onClick={() => onModeChange(mode === 'login' ? 'register' : 'login')}>
              {mode === 'login' ? 'Create an account' : 'Sign in'}
            </button>
          </div>
          <div className="auth-secure"><Icon name="shield" size={14} /> Your data is private to your account</div>
        </section>
      </div>
      <footer className="auth-footer"><span>© 2026 AutoTestReport Hub</span><span>Automated test reporting</span></footer>
    </main>
  )
}

function Overview({
  statistics,
  runs,
  flakyTests,
  loading,
  onRunClick,
  onSeeRuns,
  onSeeFlaky,
  onCreateProject,
  onUpload,
}: {
  statistics: Statistics | null
  runs: TestRun[]
  flakyTests: FlakyTest[]
  loading: boolean
  onRunClick: (run: TestRun) => void
  onSeeRuns: () => void
  onSeeFlaky: () => void
  onCreateProject: () => void
  onUpload: () => void
}) {
  if (loading && !statistics) return <LoadingPanel />
  if (!statistics) {
    return <div className="empty-state card"><h2>Start with a test report</h2><p>Upload a JUnit XML or JSON report to view metrics and test history.</p><div className="empty-actions"><button className="button button-primary" onClick={onUpload}><Icon name="upload" size={16} />Upload report</button><button className="button button-secondary" onClick={onCreateProject}>Create another project</button></div></div>
  }

  const passRate = statistics.average_pass_rate
  const chartRuns = runs.slice(0, 7).reverse()
  return (
    <>
      <section className="metric-grid">
        <MetricCard title="Total runs" value={formatNumber(statistics.total_runs)} icon="activity" tone="blue" foot={`${formatNumber(statistics.total_tests)} tests recorded`} />
        <MetricCard title="Average pass rate" value={`${passRate.toFixed(1)}%`} icon="check" tone="green" foot="Across all project runs" progress={passRate} />
        <MetricCard title="Failed tests" value={formatNumber(statistics.failed_tests)} icon="alert" tone="red" foot={statistics.total_tests ? `${((statistics.failed_tests / statistics.total_tests) * 100).toFixed(1)}% of all tests` : 'No results yet'} />
        <MetricCard title="Flaky tests" value={formatNumber(flakyTests.length)} icon="activity" tone="amber" foot="Changed outcome across runs" />
      </section>

      <section className="overview-grid">
        <div className="card chart-card">
          <div className="card-heading">
            <div><h2>Quality trend</h2><p>Results from recent test runs</p></div>
            <span className="period-tag">Recent runs</span>
          </div>
          {chartRuns.length ? (
            <>
              <div className="chart-legend"><span><i className="legend-pass" />Passed</span><span><i className="legend-fail" />Failed</span></div>
              <div className="bar-chart">
                {chartRuns.map((run) => {
                  const passHeight = run.total_tests ? Math.max(4, (run.passed_tests / run.total_tests) * 100) : 0
                  const failHeight = run.total_tests ? Math.max(0, (run.failed_tests / run.total_tests) * 100) : 0
                  return (
                    <button className="chart-column" key={run.id} title={`${formatDate(run.created_at)} · ${run.pass_rate.toFixed(1)}% passed`} onClick={() => onRunClick(run)}>
                      <span className="chart-bars"><i className="chart-failed" style={{ height: `${failHeight}%` }} /><i className="chart-passed" style={{ height: `${passHeight}%` }} /></span>
                      <small>{shortDate(run.created_at)}</small>
                    </button>
                  )
                })}
              </div>
              <div className="chart-summary"><span><span className="summary-dot" /> Average pass rate</span><strong>{passRate.toFixed(1)}%</strong></div>
            </>
          ) : (
            <div className="chart-empty"><span className="chart-empty-icon"><Icon name="bars" size={20} /></span><strong>Trend will appear after a test run</strong><span>Upload the first report to this project.</span></div>
          )}
        </div>
        <div className="card quality-card">
          <div className="card-heading"><div><h2>Test summary</h2><p>All checks in this project</p></div><span className="quality-total">{formatNumber(statistics.total_tests)}</span></div>
          <div className="quality-ring-wrap">
            <div className="quality-ring" style={{ '--pass': `${statistics.total_tests ? (statistics.passed_tests / statistics.total_tests) * 100 : 0}%`, '--fail': `${statistics.total_tests ? (statistics.failed_tests / statistics.total_tests) * 100 : 0}%` } as CSSProperties}>
              <div><strong>{passRate.toFixed(0)}%</strong><span>passed</span></div>
            </div>
          </div>
          <div className="quality-legend">
            <QualityRow label="Passed" value={statistics.passed_tests} tone="green" />
            <QualityRow label="Failed" value={statistics.failed_tests} tone="red" />
            <QualityRow label="Skipped" value={statistics.skipped_tests} tone="gray" />
          </div>
        </div>
      </section>

      <section className="card table-card">
        <div className="card-heading table-card-heading">
          <div><h2>Recent runs</h2><p>Latest imported test reports</p></div>
          {runs.length > 0 && <button className="text-button" onClick={onSeeRuns}>All runs <Icon name="arrow" size={14} /></button>}
        </div>
        {runs.length ? <RunTable runs={runs.slice(0, 5)} onRunClick={onRunClick} /> : <div className="table-empty"><Icon name="file" size={20} /><span>Upload a report to create the first run.</span><button className="text-button" onClick={onUpload}>Upload report <Icon name="arrow" size={14} /></button></div>}
      </section>

      <section className="card flaky-preview">
        <div className="flaky-preview-copy">
          <span className="flaky-icon"><Icon name="alert" size={18} /></span>
          <div><h2>Flaky tests</h2><p>Tests that passed and failed across different runs.</p></div>
        </div>
        <div className="flaky-preview-end">
          <span className={flakyTests.length ? 'flaky-badge has-flaky' : 'flaky-badge'}>{flakyTests.length ? `${flakyTests.length} found` : 'None found'}</span>
          <button className="text-button" onClick={onSeeFlaky}>View <Icon name="arrow" size={14} /></button>
        </div>
      </section>
    </>
  )
}

function MetricCard({
  title,
  value,
  icon,
  tone,
  foot,
  progress,
}: {
  title: string
  value: string
  icon: IconName
  tone: 'blue' | 'green' | 'red' | 'amber'
  foot: string
  progress?: number
}) {
  return (
    <article className="card metric-card">
      <div className="metric-top"><span>{title}</span><span className={`metric-icon ${tone}`}><Icon name={icon} size={17} /></span></div>
      <strong className="metric-value">{value}</strong>
      {progress !== undefined ? <div className="metric-progress"><i style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} /></div> : <div className="metric-spacer" />}
      <div className="metric-foot">{foot}</div>
    </article>
  )
}

function QualityRow({ label, value, tone }: { label: string; value: number; tone: string }) {
  return <div className="quality-row"><span><i className={`quality-dot ${tone}`} />{label}</span><strong>{formatNumber(value)}</strong></div>
}

function RunTable({ runs, onRunClick }: { runs: TestRun[]; onRunClick: (run: TestRun) => void }) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead><tr><th>REPORT</th><th>BRANCH / BUILD</th><th>TESTS</th><th>PASS RATE</th><th>STATUS</th><th>DATE</th><th /></tr></thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id} onClick={() => onRunClick(run)} tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter') onRunClick(run) }}>
              <td><span className={`file-type ${run.report_format}`}>{run.report_format === 'xml' ? 'XML' : 'JSON'}</span><span className="report-name">{run.source_filename}</span></td>
              <td><span className="branch-name"><Icon name="code" size={14} />{run.branch}</span><small className="build-number">{run.build_number === null ? 'Build —' : `Build #${run.build_number}`}</small></td>
              <td><strong className="test-count">{formatNumber(run.total_tests)}</strong><small className="test-breakdown"><span>{run.passed_tests} passed</span>{run.failed_tests > 0 && <span className="fail-text">{run.failed_tests} failed</span>}</small></td>
              <td><span className="pass-rate">{run.pass_rate.toFixed(1)}%</span></td>
              <td><span className={`status-pill ${run.status}`}><i />{statusLabel(run.status)}</span></td>
              <td><span className="run-date">{formatDate(run.created_at)}</span></td>
              <td><Icon name="chevron" size={15} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RunsPage({
  runs,
  loading,
  onRunClick,
}: {
  runs: TestRun[]
  loading: boolean
  onRunClick: (run: TestRun) => void
}) {
  if (loading && runs.length === 0) return <LoadingPanel />
  return (
    <section className="card page-table-card">
      <div className="card-heading table-card-heading"><div><h2>All runs</h2><p>{runs.length ? `${runs.length} recent runs` : 'Imported test results'}</p></div><span className="period-tag"><Icon name="activity" size={14} /> All branches</span></div>
      {runs.length ? <RunTable runs={runs} onRunClick={onRunClick} /> : <EmptyState title="No runs yet" copy="Upload a report in JUnit XML or JSON format." icon="file" />}
    </section>
  )
}

function FlakyPage({ tests, loading }: { tests: FlakyTest[]; loading: boolean }) {
  if (loading && tests.length === 0) return <LoadingPanel />
  return (
    <section className="card page-table-card">
      <div className="card-heading table-card-heading"><div><h2>Flaky tests</h2><p>Tests with different outcomes across runs</p></div><span className="flaky-badge">{tests.length} found</span></div>
      {tests.length ? (
        <div className="table-scroll">
          <table className="data-table flaky-table">
            <thead><tr><th>TEST</th><th>CLASS</th><th>RUNS</th><th>FAILURES</th><th>FAILURE RATE</th></tr></thead>
            <tbody>{tests.map((test) => <tr key={`${test.classname}:${test.name}`}><td><span className="report-name">{test.name}</span></td><td><span className="class-name">{test.classname || '—'}</span></td><td>{test.total_runs}</td><td><span className="fail-text">{test.failed_runs}</span></td><td><span className="flaky-rate"><i style={{ width: `${test.failure_rate}%` }} />{test.failure_rate.toFixed(1)}%</span></td></tr>)}</tbody>
          </table>
        </div>
      ) : <EmptyState title="No flaky tests found" copy="Multiple runs are needed to identify tests with changing outcomes." icon="shield" />}
    </section>
  )
}

function EmptyProjects({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="empty-project-page">
      <span className="eyebrow"><span className="eyebrow-dot" /> WORKSPACE</span>
      <h1>Create your first project</h1>
      <p>Collect test reports, track quality, and review results in one place.</p>
      <div className="empty-actions"><button className="button button-primary" onClick={onCreate}><Icon name="plus" size={16} />Create project</button></div>
    </div>
  )
}

function EmptyState({ title, copy, icon }: { title: string; copy: string; icon: IconName }) {
  return <div className="empty-state compact-empty"><span className="compact-empty-icon"><Icon name={icon} size={20} /></span><h2>{title}</h2><p>{copy}</p></div>
}

function LoadingPanel() {
  return <div className="loading-panel"><div className="loader" /><span>Loading data…</span></div>
}

function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  return (
    <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <section className="modal-card" role="dialog" aria-modal="true" aria-label={title}>
        <header className="modal-header"><h2>{title}</h2><button className="icon-button" aria-label="Close" onClick={onClose}><Icon name="close" /></button></header>
        {children}
      </section>
    </div>
  )
}

function ProjectDialog({
  mode,
  project,
  busy,
  onClose,
  onSave,
}: {
  mode: 'create' | 'edit'
  project?: Project
  busy: boolean
  onClose: () => void
  onSave: (name: string, description: string) => Promise<void>
}) {
  const [name, setName] = useState(project?.name ?? '')
  const [description, setDescription] = useState(project?.description ?? '')
  const [error, setError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    try {
      await onSave(name.trim(), description.trim())
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'The project could not be saved.')
    }
  }

  return (
    <Modal title={mode === 'create' ? 'New project' : 'Project settings'} onClose={onClose}>
      <form className="project-form" onSubmit={(event) => void submit(event)}>
        <label className="field"><span>Project name</span><input value={name} onChange={(event) => setName(event.target.value)} placeholder="For example, Web API" maxLength={100} required autoFocus /></label>
        <label className="field"><span>Description <small>(optional)</small></span><textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Briefly describe the project" maxLength={5000} rows={3} /></label>
        {error && <div className="auth-error" role="alert"><Icon name="alert" size={16} />{error}</div>}
        <div className="modal-actions"><button type="button" className="button button-secondary" onClick={onClose}>Cancel</button><button type="submit" className="button button-primary" disabled={busy}>{busy ? 'Saving…' : mode === 'create' ? 'Create project' : 'Save changes'}</button></div>
      </form>
    </Modal>
  )
}

function RunDialog({
  run,
  loading,
  error,
  onClose,
}: {
  run: TestRunDetails | null
  loading: boolean
  error: string
  onClose: () => void
}) {
  return (
    <Modal title={run?.source_filename ?? 'Run details'} onClose={onClose}>
      {loading && <LoadingPanel />}
      {error && <div className="run-dialog-error"><Icon name="alert" size={18} />{error}</div>}
      {run && (
        <div className="run-details">
          <div className="run-detail-summary">
            <span className={`status-pill ${run.status}`}><i />{statusLabel(run.status)}</span>
            <span className="detail-pass-rate">{run.pass_rate.toFixed(1)}% <small>passed</small></span>
            <div className="detail-counts"><span className="green-text">{run.passed_tests} passed</span><span className="fail-text">{run.failed_tests} failed</span><span>{run.skipped_tests} skipped</span></div>
          </div>
          <div className="run-meta-grid"><span>Branch<strong>{run.branch}</strong></span><span>Build<strong>{run.build_number === null ? '—' : `#${run.build_number}`}</strong></span><span>Duration<strong>{run.duration_seconds.toFixed(2)} s</strong></span><span>Date<strong>{formatDate(run.created_at)}</strong></span></div>
          <div className="suite-list">
            {run.suites.map((suite) => (
              <section className="suite-section" key={suite.id}>
                <div className="suite-heading"><strong>{suite.name}</strong><span>{suite.cases.length} tests</span></div>
                {suite.cases.map((test) => (
                  <div className="case-row" key={test.id}>
                    <span className={`case-indicator ${test.status}`}><Icon name={test.status === 'passed' ? 'check' : test.status === 'failed' ? 'close' : 'chevron'} size={13} /></span>
                    <span className="case-copy"><strong>{test.name}</strong><small>{test.classname || suite.name}{test.error_message && <span className="case-error">{test.error_message}</span>}</small></span>
                    <span className="case-duration">{test.duration_seconds.toFixed(2)} s</span>
                  </div>
                ))}
              </section>
            ))}
          </div>
        </div>
      )}
    </Modal>
  )
}

export default App
