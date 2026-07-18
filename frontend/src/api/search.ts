/**
 * 搜索API封装
 */
import { API_BASE } from './base'

export const searchAPI = {
  async search(params: {
    kw: string
    types?: string
    page?: number
    size?: number
    sort?: string
  }) {
    const query = new URLSearchParams()
    query.set('kw', params.kw)
    if (params.types) query.set('types', params.types)
    if (params.page) query.set('page', String(params.page))
    if (params.size) query.set('size', String(params.size))
    if (params.sort) query.set('sort', params.sort)

    const res = await fetch(`${API_BASE}/search?${query.toString()}`)
    return res.json()
  },

  async getHot(limit = 10) {
    const res = await fetch(`${API_BASE}/hot?limit=${limit}`)
    return res.json()
  },

  async getHistory(limit = 20) {
    const res = await fetch(`${API_BASE}/history?limit=${limit}`)
    return res.json()
  },

  async clearHistory() {
    const res = await fetch(`${API_BASE}/history`, { method: 'DELETE' })
    return res.json()
  },

  async getCloudTypes() {
    const res = await fetch(`${API_BASE}/sources/types`)
    return res.json()
  },

  async getSources() {
    const res = await fetch(`${API_BASE}/sources`)
    return res.json()
  },
}
