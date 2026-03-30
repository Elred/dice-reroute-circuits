import axios from 'axios'
import type { ReportRequest, ReportResponse, MetaResponse } from '../types/api'

const baseURL = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api/v1`
  : '/api/v1'

const http = axios.create({ baseURL })

export async function fetchMeta(): Promise<MetaResponse> {
  const res = await http.get<MetaResponse>('/meta')
  return res.data
}

export async function fetchReport(payload: ReportRequest): Promise<ReportResponse> {
  const { precision, ...body } = payload
  const params = precision && precision !== 'normal' ? { precision } : {}
  const res = await http.post<ReportResponse>('/report', body, { params })
  return res.data
}
