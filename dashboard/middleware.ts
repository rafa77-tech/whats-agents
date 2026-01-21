import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

interface CookieToSet {
  name: string
  value: string
  options?: CookieOptions
}

export async function middleware(request: NextRequest) {
  // Bypass de auth em desenvolvimento local
  const isDev = process.env.NEXT_PUBLIC_ENV === 'development'
  const isLocalhost = request.nextUrl.hostname === 'localhost'

  if (isDev && isLocalhost) {
    // Em dev local, permitir acesso sem autenticacao
    return NextResponse.next({ request })
  }

  let supabaseResponse = NextResponse.next({
    request,
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet: CookieToSet[]) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          supabaseResponse = NextResponse.next({
            request,
          })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options ?? {})
          )
        },
      },
    }
  )

  // IMPORTANT: Do not remove this - it refreshes the session
  const {
    data: { user },
  } = await supabase.auth.getUser()

  const isAuthRoute =
    request.nextUrl.pathname.startsWith('/login') || request.nextUrl.pathname.startsWith('/auth')
  const isApiRoute = request.nextUrl.pathname.startsWith('/api')
  const isDashboardRoute =
    request.nextUrl.pathname === '/' ||
    request.nextUrl.pathname.startsWith('/campanhas') ||
    request.nextUrl.pathname.startsWith('/sistema') ||
    request.nextUrl.pathname.startsWith('/instrucoes') ||
    request.nextUrl.pathname.startsWith('/hospitais') ||
    request.nextUrl.pathname.startsWith('/ajuda')

  // Allow API routes without auth check
  if (isApiRoute) {
    return supabaseResponse
  }

  // Redirect authenticated users away from auth routes
  if (user && isAuthRoute) {
    const url = request.nextUrl.clone()
    url.pathname = '/'
    return NextResponse.redirect(url)
  }

  // Redirect unauthenticated users to login for protected routes
  if (!user && isDashboardRoute) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }

  return supabaseResponse
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files (images, etc.)
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
