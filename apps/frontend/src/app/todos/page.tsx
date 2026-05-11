import { createClient } from '@/utils/supabase/server'
import { cookies } from 'next/headers'

export default async function Page() {
  const cookieStore = await cookies()
  const supabase = createClient(cookieStore)

  const { data: todos, error } = await supabase.from('todos').select()

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Supabase Todos Test</h1>
      {error ? (
        <div className="text-red-500 bg-red-100 p-4 rounded-md">
          <p>Error connecting to Supabase or fetching todos:</p>
          <pre className="mt-2 text-sm">{JSON.stringify(error, null, 2)}</pre>
        </div>
      ) : (
        <ul className="list-disc pl-5">
          {todos?.length === 0 && <li>No todos found (or table is empty).</li>}
          {todos?.map((todo: any) => (
            <li key={todo.id}>{todo.name}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
