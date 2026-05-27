import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'
import { BriefForm } from '../components/BriefForm'
import { createProject } from '../api/projects'

export default function NewProject() {
  const navigate = useNavigate()
  const [submitError, setSubmitError] = useState(null)

  const mutation = useMutation({
    mutationFn: createProject,
    onSuccess: (data) => {
      const id = data?.id || data?.project_id
      if (id) {
        navigate(`/projects/${id}`)
      } else {
        navigate('/')
      }
    },
    onError: (err) => {
      setSubmitError(err.message)
    },
  })

  const handleSubmit = (formData) => {
    setSubmitError(null)
    mutation.mutate(formData)
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Link
          to="/"
          className="flex items-center gap-1.5 text-slate-400 hover:text-slate-200 text-sm transition-colors"
        >
          <ArrowLeft size={16} />
          Back to Dashboard
        </Link>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
        <div className="mb-8">
          <h1 className="text-xl font-semibold text-slate-100">New Project</h1>
          <p className="text-sm text-slate-400 mt-1">
            Complete the brief to launch the AI agent pipeline
          </p>
        </div>

        <BriefForm
          onSubmit={handleSubmit}
          isSubmitting={mutation.isPending}
          submitError={submitError}
        />
      </div>
    </div>
  )
}
