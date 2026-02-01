const views = document.querySelectorAll('.view')
const navItems = document.querySelectorAll('.nav-item')
const pageTitle = document.getElementById('pageTitle')
const pageSubtitle = document.getElementById('pageSubtitle')

const subtitles = {
  home: 'Centro de comando',
  alerts: 'Alertas criticos e pendentes',
  monitor: 'Operacao em tempo real',
  health: 'Saude e disponibilidade',
  campaigns: 'Gestao de campanhas',
  conversations: 'Inbox e atendimento',
  vagas: 'Gestao de vagas',
  chips: 'Pool e instancias',
  warmup: 'Aquecimento de chips',
  grupos: 'Entrada em grupos',
  qualidade: 'Qualidade de conversas',
  auditoria: 'Historico de acoes',
  sistema: 'Configuracoes e controles',
}

function setView(targetId) {
  views.forEach((view) => view.classList.add('hidden'))
  const active = document.getElementById(targetId)
  if (active) {
    active.classList.remove('hidden')
  }

  navItems.forEach((item) => item.classList.toggle('active', item.dataset.view === targetId))
  if (pageTitle) pageTitle.textContent = targetId.charAt(0).toUpperCase() + targetId.slice(1)
  if (pageSubtitle) pageSubtitle.textContent = subtitles[targetId] || ''
  window.location.hash = targetId
}

navItems.forEach((item) => {
  item.addEventListener('click', () => setView(item.dataset.view))
})

const initialView = window.location.hash.replace('#', '') || 'home'
setView(initialView)
