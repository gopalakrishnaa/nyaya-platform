import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://fwbqxmzmixkqiropaank.supabase.co'
const supabaseKey = 'sb_publishable_AklovM7hXDOf8_chUUHvLw_3yar8kOs'
const supabase = createClient(supabaseUrl, supabaseKey)

async function check() {
  const { data, error } = await supabase.from('cases').select('*').limit(1)
  if (error) {
    console.error('Error:', error)
  } else {
    console.log('Cases table exists!', data)
  }
}

check()
