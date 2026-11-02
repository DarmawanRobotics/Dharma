// The Dharma documentation site: which Markdown of this repository becomes which page.
// Every page stays a file of the repository (docs/guide, READMEs); scripts/sync.mjs copies them.
const g = (file, dest, text) => ({ src: `docs/guide/${file}.md`, dest, text })

export default {
  title: 'Dharma',
  description:
    'A robot-agnostic ROS 2 autonomy stack for legged and wheeled service robots: odometry, ' +
    'fiducial localization, mapping, navigation, a safety mux, health and a simulator.',
  repo: 'DarmawanRobotics/Dharma',
  branch: 'main',
  logo: 'logo.svg',
  brand: { light: '#3d5f99', light2: '#5679b5', dark: '#8fb0ea', dark2: '#a9c3f2', soft: 'rgba(61,95,153,.16)' },
  copyright: 'Apache-2.0 · DarmawanRobotics',
  sections: [
    {
      text: 'Guide',
      items: [
        g('README', 'guide/introduction', 'Introduction'),
        g('Getting-Started', 'guide/getting-started', 'Getting Started'),
        g('Architecture', 'guide/architecture', 'Architecture'),
        g('Robot-Profile', 'guide/robot-profile', 'Robot Profile'),
        g('Topics-and-Services', 'guide/topics-and-services', 'Topics and Services'),
        g('New-Product-from-Template', 'guide/new-product', 'New Product from Template'),
      ],
    },
    {
      text: 'Subsystems',
      items: [
        g('Safety', 'subsystems/safety', 'Safety'),
        g('Localization', 'subsystems/localization', 'Localization'),
        g('Mapping-and-Sites', 'subsystems/mapping-and-sites', 'Mapping and Sites'),
        g('Navigation', 'subsystems/navigation', 'Navigation'),
        g('Health', 'subsystems/health', 'Health'),
        g('Simulation', 'subsystems/simulation', 'Simulation'),
      ],
    },
    {
      text: 'Operate',
      items: [
        g('Tuning', 'operate/tuning', 'Tuning'),
        g('Troubleshooting', 'operate/troubleshooting', 'Troubleshooting'),
        g('FAQ', 'operate/faq', 'FAQ'),
      ],
    },
    {
      text: 'Reference',
      items: [
        { src: 'README.md', dest: 'reference/hub', text: 'The hub repository' },
        { src: 'src/robot_bringup/README.md', dest: 'reference/robot-bringup', text: 'robot_bringup' },
        { src: 'experiments/README.md', dest: 'reference/experiments', text: 'Experiments' },
        { src: 'docs/README.md', dest: 'reference/documents', text: 'Documents' },
        g('Contributing', 'reference/contributing', 'Contributing'),
        { src: 'CHANGELOG.md', dest: 'reference/changelog', text: 'Changelog' },
      ],
    },
  ],
  files: [
    { src: 'docs/pdf/dharma_manual.pdf', as: 'dharma_manual.pdf', text: 'Technical manual' },
    { src: 'docs/pdf/dharma_paper.pdf', as: 'dharma_paper.pdf', text: 'Paper' },
  ],
}
