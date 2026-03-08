import { useEffect, useState } from 'react'
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd'
import { API } from '../context/AuthContext'
import { Loader2, GripVertical, Building2 } from 'lucide-react'

const COLUMNS = [
  { id: 'Applied',             label: 'Applied',             color: 'border-blue-500/40',    dot: 'bg-blue-400' },
  { id: 'OA Received',         label: 'OA Received',         color: 'border-amber-500/40',   dot: 'bg-amber-400' },
  { id: 'Interview Scheduled', label: 'Interview',           color: 'border-violet-500/40',  dot: 'bg-violet-400' },
  { id: 'Selected',            label: 'Selected',            color: 'border-emerald-500/40', dot: 'bg-emerald-400' },
  { id: 'Rejected',            label: 'Rejected',            color: 'border-red-500/40',     dot: 'bg-red-400' },
]

export default function Kanban() {
  const [apps, setApps] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    API.get('/applications').then(r => setApps(r.data)).finally(() => setLoading(false))
  }, [])

  const onDragEnd = async (result) => {
    const { draggableId, destination } = result
    if (!destination) return

    const newStatus = destination.droppableId
    const appId = parseInt(draggableId)

    setApps(prev => prev.map(a => a.id === appId ? { ...a, status: newStatus } : a))
    try {
      await API.patch(`/applications/${appId}/status`, { status: newStatus })
    } catch {
      API.get('/applications').then(r => setApps(r.data))
    }
  }

  const byStatus = (status) => apps.filter(a => a.status === status)

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <Loader2 size={28} className="animate-spin text-violet-400" />
    </div>
  )

  return (
    <div className="font-['Sora',sans-serif] space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Kanban Board</h1>
        <p className="text-white/40 text-sm mt-0.5">Drag and drop to update application status</p>
      </div>

      <DragDropContext onDragEnd={onDragEnd}>
        <div className="flex gap-4 overflow-x-auto pb-4">
          {COLUMNS.map(col => (
            <div key={col.id} className="flex-shrink-0 w-64">
              {/* Column header */}
              <div className={`flex items-center gap-2 mb-3 px-3 py-2 rounded-xl border ${col.color} bg-white/2`}>
                <div className={`w-2 h-2 rounded-full ${col.dot}`} />
                <span className="text-sm font-medium text-white/70">{col.label}</span>
                <span className="ml-auto text-xs text-white/30 bg-white/5 px-2 py-0.5 rounded-full">
                  {byStatus(col.id).length}
                </span>
              </div>

              {/* Droppable area */}
              <Droppable droppableId={col.id}>
                {(provided, snapshot) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    className={`min-h-32 rounded-xl space-y-2 p-2 transition-colors ${snapshot.isDraggingOver ? 'bg-violet-500/5 border border-violet-500/20' : 'bg-white/2 border border-transparent'}`}
                  >
                    {byStatus(col.id).map((app, index) => (
                      <Draggable key={app.id} draggableId={String(app.id)} index={index}>
                        {(provided, snapshot) => (
                          <div
                            ref={provided.innerRef}
                            {...provided.draggableProps}
                            className={`bg-[#13151f] border rounded-xl p-3 transition-all ${snapshot.isDragging ? 'border-violet-500/50 shadow-xl shadow-violet-500/20 rotate-1' : 'border-white/8 hover:border-white/15'}`}
                          >
                            <div className="flex items-start gap-2">
                              <div {...provided.dragHandleProps} className="mt-0.5 text-white/20 hover:text-white/50 cursor-grab active:cursor-grabbing">
                                <GripVertical size={14} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-1.5 mb-1">
                                  <Building2 size={12} className="text-white/30 flex-shrink-0" />
                                  <p className="text-sm font-semibold text-white truncate">{app.company}</p>
                                </div>
                                <p className="text-xs text-white/40 truncate pl-4">{app.role}</p>
                                {app.applied_date && (
                                  <p className="text-[10px] text-white/20 mt-2 pl-4">
                                    {new Date(app.applied_date).toLocaleDateString()}
                                  </p>
                                )}
                              </div>
                            </div>
                          </div>
                        )}
                      </Draggable>
                    ))}
                    {provided.placeholder}

                    {byStatus(col.id).length === 0 && !snapshot.isDraggingOver && (
                      <div className="flex items-center justify-center h-20 text-white/15 text-xs">
                        Drop here
                      </div>
                    )}
                  </div>
                )}
              </Droppable>
            </div>
          ))}
        </div>
      </DragDropContext>
    </div>
  )
}