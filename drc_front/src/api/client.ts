import axios from 'axios'
import type { ReportRequest, ReportResponse, MetaResponse } from '../types/api'

const http = axios.create({ baseURL: '/api/v1' })

export async function fetchMeta(): Promise<MetaResponse> {
  const res = await http.get<MetaResponse>('/meta')
  return res.data
}

export async function fetchReport(payload: ReportRequest): Promise<ReportResponse> {
  const res = await http.post<ReportResponse>('/report', payload)
  return res.data
}
