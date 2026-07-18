const GATEWAY_PREFIX = '/app/third-pan-search'

const isGatewayPath = window.location.pathname === GATEWAY_PREFIX
  || window.location.pathname.startsWith(`${GATEWAY_PREFIX}/`)

export const API_BASE = isGatewayPath ? `${GATEWAY_PREFIX}/api` : '/api'
