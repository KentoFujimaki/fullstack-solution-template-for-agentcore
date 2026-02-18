import { PropsWithChildren, useEffect, useMemo, useState } from "react"
import { CopilotKit } from "@copilotkit/react-core"
import { cognitoAuthConfig, createCognitoAuthConfig } from "@/lib/auth"

const DEFAULT_RUNTIME_URL = "/invocations"

function getAccessTokenFromStorage(authority?: string, clientId?: string): string | null {
  if (!authority || !clientId || typeof window === "undefined") {
    return null
  }

  const storageKey = `oidc.user:${authority}:${clientId}`
  const raw = window.localStorage.getItem(storageKey)
  if (!raw) {
    return null
  }

  try {
    const parsed = JSON.parse(raw) as { access_token?: string }
    return parsed.access_token ?? null
  } catch {
    return null
  }
}

export function CopilotKitProvider({ children }: PropsWithChildren) {
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const runtimeUrl = import.meta.env.VITE_AGUI_ENDPOINT_URL || DEFAULT_RUNTIME_URL

  useEffect(() => {
    let active = true

    async function resolveToken() {
      try {
        const config = await createCognitoAuthConfig()
        const token =
          getAccessTokenFromStorage(config.authority, config.client_id) ??
          getAccessTokenFromStorage(cognitoAuthConfig.authority, cognitoAuthConfig.client_id)
        if (active) {
          setAccessToken(token)
        }
      } catch {
        const fallbackToken = getAccessTokenFromStorage(
          cognitoAuthConfig.authority,
          cognitoAuthConfig.client_id
        )
        if (active) {
          setAccessToken(fallbackToken)
        }
      }
    }

    resolveToken()

    return () => {
      active = false
    }
  }, [])

  // 既存 OIDC 保存形式から取り出した token を Authorization ヘッダーへ渡す
  const headers = useMemo(() => {
    if (!accessToken) {
      return {}
    }

    return {
      Authorization: `Bearer ${accessToken}`,
    }
  }, [accessToken])

  return (
    <CopilotKit runtimeUrl={runtimeUrl} headers={headers}>
      {children}
    </CopilotKit>
  )
}
