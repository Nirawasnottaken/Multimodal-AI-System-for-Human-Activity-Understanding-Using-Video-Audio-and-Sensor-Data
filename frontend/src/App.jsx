import { useEffect, useMemo, useState } from 'react'
import { Activity, ArrowUpRight, Check, ChevronDown, Code2, Download, FileCode2, FileText, Folder, Github, LoaderCircle, Plus, Rocket, ShieldCheck, Sparkles, UploadCloud, X } from 'lucide-react'

const frameworks = ['React + FastAPI', 'Python + FastAPI', 'Next.js + TypeScript', 'Node.js + Express', 'Python CLI', 'Java + Spring Boot', 'C++', 'Custom / choose for me']
const api = async (url, options={}) => {
  const res = await fetch(url, { credentials: 'include', ...options })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`)
  return data
}
const formatSize = n => n < 1024 ? `${n} B` : `${(n/1024).toFixed(1)} KB`
const iconFor = name => name.endsWith('.md') || name.endsWith('.txt') ? FileText : FileCode2

export default function App() {
  const [topic, setTopic] = useState('Multimodal AI System for Human Activity Understanding Using Video, Audio, and Sensor Data')
  const [framework, setFramework] = useState(frameworks[0])
  const [uploads, setUploads] = useState([])
  const [project, setProject] = useState(null)
  const [files, setFiles] = useState([])
  const [selected, setSelected] = useState('')
  const [preview, setPreview] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState({type:'', text:''})
  const [githubConnected, setGithubConnected] = useState(false)
  const [repos, setRepos] = useState([])
  const [repoMode, setRepoMode] = useState('new')
  const [repoName, setRepoName] = useState('multimodal-human-activity-ai')
  const [existingRepo, setExistingRepo] = useState('')
  const [description, setDescription] = useState('AI-generated multimodal human activity understanding system')
  const [branch, setBranch] = useState('main')
  const [visibility, setVisibility] = useState('private')
  const [confirmPublish, setConfirmPublish] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [published, setPublished] = useState(null)
  const [analysis, setAnalysis] = useState(null)

  useEffect(() => {
    api('/api/github/status').then(x => setGithubConnected(x.connected)).catch(()=>{})
    const params = new URLSearchParams(location.search)
    if (params.has('github')) { setMessage({type:'success',text:'GitHub connected successfully.'}); history.replaceState({},'',location.pathname) }
    if (params.has('github_error')) { setMessage({type:'error',text:'GitHub authorization was cancelled or denied.'}); history.replaceState({},'',location.pathname) }
  }, [])

  const loadFiles = async id => {
    const result = await api(`/api/projects/${id}/files`)
    setFiles(result.files)
    if (result.files.length) await openFile(id, result.files[0].path)
  }
  const openFile = async (id, path) => {
    try { const data = await api(`/api/projects/${id}/file?path=${encodeURIComponent(path)}`); setSelected(path); setPreview(data.content) }
    catch(e) { setMessage({type:'error',text:e.message}) }
  }
  const formData = () => {
    const data = new FormData()
    data.append('topic', topic)
    data.append('framework', framework)
    uploads.forEach(f => data.append('files', f))
    return data
  }
  const analyze = async () => {
    setLoading(true); setMessage({type:'',text:''})
    try {
      const data = new FormData(); data.append('topic', topic); uploads.forEach(f => data.append('files',f))
      const result = await api('/api/projects/analyze',{method:'POST',body:data})
      setTopic(result.specification); setAnalysis(result)
      setMessage({type:'success',text:`Specification analyzed · ${result.characters.toLocaleString()} characters extracted.`})
    } catch(e) { setMessage({type:'error',text:e.message}) } finally { setLoading(false) }
  }
  const generate = async () => {
    setLoading(true); setMessage({type:'',text:''}); setProject(null); setFiles([]); setPreview(''); setPublished(null)
    try {
      const result = await api('/api/projects/generate',{method:'POST',body:formData()})
      setProject(result); await loadFiles(result.project_id)
      setMessage({type:'success',text:`Project generated with ${result.count} files. Review the source before running or publishing.`})
    } catch(e) { setMessage({type:'error',text:e.message}) } finally { setLoading(false) }
  }
  const connectGithub = () => { location.href = '/api/github/login' }
  const loadRepos = async () => {
    try { const data = await api('/api/github/repositories'); setRepos(data.repositories); if(!existingRepo && data.repositories.length) setExistingRepo(data.repositories[0].full_name) }
    catch(e) { setMessage({type:'error',text:e.message}) }
  }
  useEffect(()=>{ if(githubConnected) loadRepos() },[githubConnected])
  const publish = async () => {
    if(!project || !confirmPublish) return
    setPublishing(true); setMessage({type:'',text:''})
    try {
      const body = {project_id:project.project_id, confirm:true, branch, description, private:visibility==='private', commit_message:'Add AI-generated project'}
      if(repoMode==='new') body.repository=repoName
      else body.existing_repository=existingRepo
      const result = await api('/api/github/publish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
      setPublished(result); setMessage({type:'success',text:`Published ${result.published_files} files to GitHub.`})
    } catch(e) { setMessage({type:'error',text:e.message}) } finally { setPublishing(false) }
  }
  const grouped = useMemo(()=> {
    const groups = {}
    files.forEach(f=> { const parts=f.path.split('/'); const key=parts.length>1?parts.slice(0,-1).join('/'):'.'; (groups[key] ||= []).push(f) })
    return groups
  },[files])

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-icon"><Code2 size={21}/></div><div><strong>AI Project Builder</strong><span>DEVELOPER WORKSPACE</span></div></div>
      <div className="workspace-label">WORKSPACE</div>
      <button className="nav-item active"><Activity size={17}/> Project Studio <span className="nav-dot"/></button>
      <button className="nav-item" onClick={()=>document.getElementById('files-section')?.scrollIntoView({behavior:'smooth'})}><Folder size={17}/> Generated files</button>
      <button className="nav-item" onClick={()=>document.getElementById('github-section')?.scrollIntoView({behavior:'smooth'})}><Github size={17}/> GitHub publishing</button>
      <div className="sidebar-bottom"><div className="secure-card"><ShieldCheck size={18}/><div><b>Private by design</b><p>Provider keys stay on the server. Review every file before publishing.</p></div></div><div className="user-mini"><div className="avatar">AI</div><div><b>Builder workspace</b><span>Local development</span></div><ChevronDown size={15}/></div></div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="crumb">Workspace <span>/</span> <b>Project Studio</b></div><div className="top-actions"><span className="status-pill"><i/> API workspace</span><a className="docs-link" href="http://localhost:8000/docs" target="_blank" rel="noreferrer">API docs <ArrowUpRight size={14}/></a></div></header>
      <section className="hero"><div><div className="eyebrow"><Sparkles size={14}/> FROM IDEA TO REPOSITORY</div><h1>Build something<br/><em>remarkable.</em></h1><p>Turn a project brief into a structured codebase. Inspect the output, download it, or publish it to GitHub when you're ready.</p></div><div className="hero-art" aria-hidden="true"><div className="orbit orbit-a"/><div className="orbit orbit-b"/><div className="core"><Code2 size={35}/></div><span className="float-tag tag-a">AI / BUILD</span><span className="float-tag tag-b">01 — 09</span><span className="float-tag tag-c">SOURCE READY</span></div></section>
      {message.text && <div className={`notice ${message.type}`} role="status"><span>{message.type==='success'?<Check size={17}/>:<X size={17}/>}</span>{message.text}<button onClick={()=>setMessage({type:'',text:''})} aria-label="Dismiss"><X size={15}/></button></div>}
      <div className="section-heading"><div><span className="section-index">01</span><div><h2>Project specification</h2><p>Describe what you want to build. Attach a brief if you have one.</p></div></div><span className="step-state"><i/> READY FOR INPUT</span></div>
      <section className="builder-grid">
        <div className="panel spec-panel">
          <div className="panel-head"><div className="panel-title"><span className="mini-icon"><Sparkles size={16}/></span><div><b>Project brief</b><small>Topic, goals, requirements, constraints</small></div></div><span className="optional">REQUIRED</span></div>
          <textarea className="topic-input" value={topic} onChange={e=>setTopic(e.target.value)} placeholder="Describe your project, its features, users, preferred architecture, and constraints..." aria-label="Project topic and requirements"/>
          <div className="input-footer"><span>{topic.length.toLocaleString()} characters</span><span>Be specific for better results</span></div>
          <label className="upload-zone"><input type="file" multiple accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.webp,.bmp" onChange={e=>setUploads(Array.from(e.target.files||[]))}/><div className="upload-icon"><UploadCloud size={21}/></div><div><b>Drop files here or <u>browse files</u></b><small>PDF, DOCX, TXT, Markdown or image · max 10 MB each</small></div><Plus size={17} className="upload-plus"/></label>
          {uploads.length>0 && <div className="upload-list">{uploads.map((f,i)=><div className="upload-file" key={f.name+i}><FileText size={15}/><span>{f.name}</span><small>{formatSize(f.size)}</small><button onClick={()=>setUploads(uploads.filter((_,j)=>j!==i))} aria-label={`Remove ${f.name}`}><X size={14}/></button></div>)}</div>}
          <div className="framework-row"><label htmlFor="framework">Preferred stack</label><select id="framework" value={framework} onChange={e=>setFramework(e.target.value)}>{frameworks.map(f=><option key={f}>{f}</option>)}</select></div>
          <div className="button-row"><button className="btn secondary" onClick={analyze} disabled={loading}><FileText size={16}/> Analyze brief</button><button className="btn primary" onClick={generate} disabled={loading||(!topic.trim()&&!uploads.length)}>{loading?<LoaderCircle className="spin" size={17}/>:<Sparkles size={16}/>} {loading?'Generating project…':'Generate project'} <ArrowUpRight size={16}/></button></div>
          {analysis && <div className="analysis-card"><b>Specification analyzed</b><p>{analysis.summary}</p></div>}
        </div>
        <div className="side-column">
          <div className="panel checklist"><div className="panel-head"><div className="panel-title"><span className="mini-icon purple"><Rocket size={16}/></span><div><b>Build pipeline</b><small>Your generation workflow</small></div></div></div>
            {['Analyze requirements','Generate source files','Review code & structure','Download ZIP or publish'].map((s,i)=><div className="pipeline-row" key={s}><div className={`pipeline-number ${project&&i<3?'done':loading&&i===1?'working':''}`}>{project&&i<3?<Check size={13}/>:String(i+1).padStart(2,'0')}</div><div><b>{s}</b><small>{['Understand your brief','Create project files with AI','Preview files before use','Choose your delivery method'][i]}</small></div><span className={`pipeline-state ${project&&i<3?'complete':''}`}>{project&&i<3?'DONE':loading&&i===1?'RUNNING':i===3?'NEXT':'WAITING'}</span></div>)}
          </div>
          <div className="tip-card"><div className="tip-icon"><ShieldCheck size={17}/></div><div><b>Safety built in</b><p>Credentials and local environment files are excluded from ZIPs and GitHub publishing. Always inspect generated code before running it.</p></div></div>
        </div>
      </section>
      <section id="files-section" className="files-section">
        <div className="section-heading"><div><span className="section-index">02</span><div><h2>Generated codebase</h2><p>{project?`${files.length} files ready to inspect`:'Your generated files will appear here'}</p></div></div><div className="section-tools">{project&&<><span className="file-count">{files.length} FILES</span><a className="btn secondary download-btn" href={`/api/projects/${project.project_id}/download`}><Download size={16}/> Download ZIP</a></>}</div></div>
        <div className={`code-workspace ${!project?'empty-workspace':''}`}>
          {!project ? <div className="empty-state"><div className="empty-graphic"><Folder size={30}/><Sparkles size={17}/></div><h3>Your workspace is waiting</h3><p>Generate a project to browse its folder structure, preview source files, and download a ZIP.</p><span><Code2 size={14}/> Source files · README · Dependencies</span></div> :
          <><div className="file-browser"><div className="file-browser-head"><span><Folder size={15}/> generated-project</span><span>{files.length}</span></div><div className="file-tree">{files.map(f=>{const I=iconFor(f.path);return <button key={f.path} className={`file-row ${selected===f.path?'selected':''}`} onClick={()=>openFile(project.project_id,f.path)} title={f.path}><I size={15}/><span>{f.path}</span><small>{formatSize(f.size)}</small></button>})}</div></div><div className="code-preview"><div className="preview-head"><div><span className="traffic"><i/><i/><i/></span><b>{selected||'Select a file'}</b></div><button className="copy-btn" onClick={()=>navigator.clipboard?.writeText(preview)} disabled={!preview}>Copy code</button></div><pre><code>{preview||'Select a file from the explorer to preview its contents.'}</code></pre></div></>}
        </div>
      </section>
      <section id="github-section" className="github-section">
        <div className="section-heading"><div><span className="section-index">03</span><div><h2>Publish to GitHub</h2><p>Connect your account and review the destination before committing.</p></div></div><span className={`connection-pill ${githubConnected?'connected':''}`}><i/>{githubConnected?'CONNECTED':'NOT CONNECTED'}</span></div>
        <div className="panel github-panel"><div className="github-intro"><div className="github-mark"><Github size={25}/></div><div><h3>{githubConnected?'GitHub account connected':'Your code, one repository away'}</h3><p>{githubConnected?'Choose a repository destination below. Publishing requires explicit confirmation.':'Authorize with GitHub OAuth. Your password is never requested by this app.'}</p></div>{!githubConnected&&<button className="btn primary connect-btn" onClick={connectGithub}><Github size={16}/> Connect GitHub <ArrowUpRight size={15}/></button>}</div>
          {githubConnected&&<><div className="repo-tabs"><button className={repoMode==='new'?'active':''} onClick={()=>setRepoMode('new')}><Plus size={15}/> Create new repository</button><button className={repoMode==='existing'?'active':''} onClick={()=>setRepoMode('existing')}><Folder size={15}/> Existing repository</button></div>
          <div className="repo-form">
            {repoMode==='new'?<><div className="field"><label htmlFor="repo-name">Repository name</label><input id="repo-name" value={repoName} onChange={e=>setRepoName(e.target.value)} placeholder="my-ai-project"/></div><div className="field"><label htmlFor="repo-desc">Description</label><input id="repo-desc" value={description} onChange={e=>setDescription(e.target.value)} maxLength={350}/></div><div className="field short"><label htmlFor="visibility">Visibility</label><select id="visibility" value={visibility} onChange={e=>setVisibility(e.target.value)}><option value="private">Private</option><option value="public">Public</option></select></div></>:<><div className="field"><label htmlFor="existing">Repository</label><select id="existing" value={existingRepo} onChange={e=>setExistingRepo(e.target.value)}><option value="">Select repository…</option>{repos.map(r=><option key={r.full_name} value={r.full_name}>{r.full_name} {r.private?'(private)':'(public)'}</option>)}</select></div><button className="btn secondary" onClick={loadRepos}>Refresh repositories</button></>}
            <div className="field short"><label htmlFor="branch">Target branch</label><input id="branch" value={branch} onChange={e=>setBranch(e.target.value)} placeholder="main"/></div>
          </div>
          <div className="publish-confirm"><label className="check-label"><input type="checkbox" checked={confirmPublish} onChange={e=>setConfirmPublish(e.target.checked)}/><span>I reviewed the generated files and confirm publishing or updating the selected repository.</span></label><button className="btn primary" onClick={publish} disabled={!project||!confirmPublish||publishing||(repoMode==='new'&&!repoName.trim())||(repoMode==='existing'&&!existingRepo)}>{publishing?<LoaderCircle size={16} className="spin"/>:<Rocket size={16}/>} {publishing?'Publishing…':'Publish project'} <ArrowUpRight size={15}/></button></div>
          {published&&<div className="published-result"><Check size={18}/><div><b>Repository updated successfully</b><p>{published.published_files} files committed · {published.commit_sha?.slice(0,7)||'commit confirmed'}</p><a href={published.url} target="_blank" rel="noreferrer">{published.url} <ArrowUpRight size={13}/></a></div></div>}
          <p className="scope-note"><ShieldCheck size={14}/> GitHub OAuth requests repository access to create private repositories and push commits. Revoke access any time in GitHub settings.</p></>}
        </div>
      </section>
      <footer><div className="brand tiny"><div className="brand-icon"><Code2 size={15}/></div><strong>AI Project Builder</strong></div><span>Build responsibly. Review before you run.</span><span>Local development workspace</span></footer>
    </main>
  </div>
}
