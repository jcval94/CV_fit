from __future__ import annotations

from cv_agent.schemas import CVDocument


HEADINGS = {
    "en": {
        "summary": "Professional Summary",
        "experience": "Experience",
        "projects": "Selected Projects",
        "skills": "Skills",
        "education": "Education",
        "certifications": "Certifications",
    },
    "es": {
        "summary": "Resumen Profesional",
        "experience": "Experiencia",
        "projects": "Proyectos Seleccionados",
        "skills": "Habilidades",
        "education": "Formación",
        "certifications": "Certificaciones",
    },
    "fr": {
        "summary": "Résumé Professionnel",
        "experience": "Expérience",
        "projects": "Projets Sélectionnés",
        "skills": "Compétences",
        "education": "Formation",
        "certifications": "Certifications",
    },
}


def render_markdown(cv: CVDocument) -> str:
    headings = HEADINGS.get(cv.language, HEADINGS["en"])
    lines = [f"# {cv.headline.text}", "", f"**{cv.target_role}**", "", f"## {headings['summary']}", "", cv.summary.text, ""]

    lines.extend([f"## {headings['experience']}", ""])
    for item in cv.experience:
        lines.extend([f"### {item.title} — {item.organization}", f"*{item.period}*", ""])
        lines.extend(f"- {bullet.text}" for bullet in item.bullets)
        lines.append("")

    if cv.projects:
        lines.extend([f"## {headings['projects']}", ""])
        for item in cv.projects:
            lines.append(f"### {item.name}")
            lines.extend(f"- {bullet.text}" for bullet in item.bullets)
            lines.append("")

    lines.extend([f"## {headings['skills']}", ""])
    lines.extend(f"- {line.text}" for line in cv.skills)
    lines.append("")

    if cv.education:
        lines.extend([f"## {headings['education']}", ""])
        lines.extend(f"- {line.text}" for line in cv.education)
        lines.append("")

    if cv.certifications:
        lines.extend([f"## {headings['certifications']}", ""])
        lines.extend(f"- {line.text}" for line in cv.certifications)
        lines.append("")

    return "\n".join(lines).strip() + "\n"
