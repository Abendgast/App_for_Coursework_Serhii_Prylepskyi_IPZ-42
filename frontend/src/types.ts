export interface User {
  id: string
  email: string
  display_name: string
  is_active: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface Project {
  id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
  runs_count: number
}

export interface CreatedProject extends Project {
  api_key: string
}

export interface Statistics {
  project_id: string
  total_runs: number
  total_tests: number
  passed_tests: number
  failed_tests: number
  skipped_tests: number
  average_pass_rate: number
  latest_run_id: string | null
  latest_run_status: string | null
}

export interface TestRun {
  id: string
  project_id: string
  source_filename: string
  report_format: string
  build_number: number | null
  branch: string
  status: string
  total_tests: number
  passed_tests: number
  failed_tests: number
  skipped_tests: number
  duration_seconds: number
  pass_rate: number
  created_at: string
}

export interface TestCase {
  id: string
  classname: string
  name: string
  status: string
  duration_seconds: number
  error_message: string | null
}

export interface TestSuite {
  id: string
  name: string
  cases: TestCase[]
}

export interface TestRunDetails extends TestRun {
  suites: TestSuite[]
}

export interface RunList {
  items: TestRun[]
  total: number
}

export interface FlakyTest {
  classname: string
  name: string
  total_runs: number
  failed_runs: number
  failure_rate: number
}
