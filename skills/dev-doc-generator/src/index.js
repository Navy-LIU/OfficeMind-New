#!/usr/bin/env node

// CLI Tool: DevDoc Generator
// Usage: devdoc <project-name> "your development requirements"
// Generates development documentation and task breakdown in Markdown format

import { Command } from 'commander';
import { generateDocumentation } from './doc-generator.js';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { join } from 'path';

const program = new Command();

program
  .name('devdoc')
  .description('Generate development documentation and task breakdown from requirements')
  .version('1.0.0')
  .argument('<project-name>', 'Name of the project')
  .argument('<requirements>', 'Development requirements (quoted string)')
  .option('-o, --output <dir>', 'Output directory (default: current directory)', './output')
  .option('-p, --project <path>', 'Project path (default: ./dev-docs/<project-name>)', './dev-docs')
  .parse();

const options = program.opts();
const projectName = program.args[0];
const requirements = program.args[1];

async function main() {
  console.log('\n🚀 DevDoc Generator - Development Documentation & Task Breakdown');
  console.log('=====================================');
  console.log('Project:', projectName);
  console.log('Requirements:', requirements);
  console.log('\n📝 Generating documentation...\n');

  // Generate documentation
  const doc = generateDocumentation({
    projectName,
    requirements,
    options
  });

  // Create output directory
  const outputDir = join(process.cwd(), options.project);
  if (!existsSync(outputDir)) {
    mkdirSync(outputDir, { recursive: true });
    console.log('📁 Created output directory:', outputDir);
  }

  // Write main documentation file
  const docFilePath = join(outputDir, `${projectName.toLowerCase().replace(/\s+/g, '-')}-dev-doc.md`);
  writeFileSync(docFilePath, doc.content);
  console.log('📄 Document created:', docFilePath);

  // Write task breakdown file
  const taskFilePath = join(outputDir, `${projectName.toLowerCase().replace(/\s+/g, '-')}-tasks.md`);
  writeFileSync(taskFilePath, doc.tasks);
  console.log('📋 Task breakdown created:', taskFilePath);

  // Summary
  console.log('\n✨ Generation complete!');
  console.log('   Total sections:', doc.sectionCount);
  console.log('   Total tasks:', doc.taskCount);
  console.log('   Output path:', outputDir);
  console.log('\n📂 Run ls ' + outputDir + ' to view generated files\n');
}

main().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
