/**
 * API: POST /api/upload
 *
 * Upload de arquivos para Supabase Storage.
 * Retorna URL pública para envio via WhatsApp.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

const BUCKET_NAME = 'chat-media'
const MAX_FILE_SIZE = 16 * 1024 * 1024 // 16MB

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const file = formData.get('file') as File | null
    const type = formData.get('type') as string | null // image, audio, document

    if (!file) {
      return NextResponse.json({ error: 'Arquivo é obrigatório' }, { status: 400 })
    }

    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json({ error: 'Arquivo muito grande (máximo 16MB)' }, { status: 400 })
    }

    const supabase = createAdminClient()

    // Generate unique filename
    const ext = file.name.split('.').pop() || 'bin'
    const timestamp = Date.now()
    const random = Math.random().toString(36).substring(2, 8)
    const folder = type || 'files'
    const filename = `${folder}/${timestamp}-${random}.${ext}`

    // Convert File to ArrayBuffer then to Buffer
    const arrayBuffer = await file.arrayBuffer()
    const buffer = Buffer.from(arrayBuffer)

    // Upload to Supabase Storage
    const { data, error } = await supabase.storage.from(BUCKET_NAME).upload(filename, buffer, {
      contentType: file.type,
      upsert: false,
    })

    if (error) {
      console.error('Upload error:', error)

      // Check if bucket exists
      if (error.message?.includes('Bucket not found')) {
        // Try to create bucket
        const { error: bucketError } = await supabase.storage.createBucket(BUCKET_NAME, {
          public: true,
          fileSizeLimit: MAX_FILE_SIZE,
        })

        if (bucketError) {
          console.error('Bucket creation error:', bucketError)
          return NextResponse.json({ error: 'Erro ao criar bucket de storage' }, { status: 500 })
        }

        // Retry upload
        const { data: retryData, error: retryError } = await supabase.storage
          .from(BUCKET_NAME)
          .upload(filename, buffer, {
            contentType: file.type,
            upsert: false,
          })

        if (retryError) {
          console.error('Retry upload error:', retryError)
          return NextResponse.json({ error: 'Erro ao fazer upload' }, { status: 500 })
        }

        // Get public URL
        const {
          data: { publicUrl },
        } = supabase.storage.from(BUCKET_NAME).getPublicUrl(retryData.path)

        return NextResponse.json({
          success: true,
          url: publicUrl,
          path: retryData.path,
          type: type || 'document',
        })
      }

      return NextResponse.json({ error: 'Erro ao fazer upload' }, { status: 500 })
    }

    // Get public URL
    const {
      data: { publicUrl },
    } = supabase.storage.from(BUCKET_NAME).getPublicUrl(data.path)

    return NextResponse.json({
      success: true,
      url: publicUrl,
      path: data.path,
      type: type || 'document',
    })
  } catch (error) {
    console.error('Erro no upload:', error)
    return NextResponse.json({ error: 'Erro ao processar upload' }, { status: 500 })
  }
}
