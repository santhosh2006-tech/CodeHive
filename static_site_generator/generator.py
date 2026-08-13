import os
import markdown
from jinja2 import Template

def generate_site():
    content_dir = "content"
    template_path = os.path.join("templates", "layout.html")
    public_dir = "public"

    if not os.path.exists(content_dir):
        print(f"Error: Content directory '{content_dir}' not found.")
        return
    if not os.path.exists(template_path):
        print(f"Error: Template layout '{template_path}' not found.")
        return

    os.makedirs(public_dir, exist_ok=True)

    # Read template layout
    with open(template_path, "r", encoding="utf-8") as f:
        layout_src = f.read()
    template = Template(layout_src)

    # Convert all markdown files in content/ to HTML in public/
    count = 0
    for filename in os.listdir(content_dir):
        if filename.endswith(".md"):
            md_path = os.path.join(content_dir, filename)
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()

            html_body = markdown.markdown(md_content)
            rendered = template.render(content=html_body)

            out_filename = os.path.splitext(filename)[0] + ".html"
            out_path = os.path.join(public_dir, out_filename)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(rendered)
            print(f"Generated: {md_path} -> {out_path}")
            count += 1

    print(f"Static site generation complete. Generated {count} pages.")

if __name__ == "__main__":
    generate_site()
