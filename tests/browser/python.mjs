/* Which interpreter runs the page fixture builders.

   The fixtures import bs4, so they need the interpreter that has the project's requirements
   installed. On CI that is `python`; in a development sandbox it is usually a virtualenv whose
   python is not on PATH, and silently running the wrong one fails inside beforeAll with a
   ModuleNotFoundError that looks like a page defect. PYTHON still wins, so CI is unchanged. */
import fs from 'node:fs';

export function python() {
  if (process.env.PYTHON) return process.env.PYTHON;
  for (const candidate of ['.venv/bin/python', 'venv/bin/python', '.venv\\Scripts\\python.exe']) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return 'python';
}
