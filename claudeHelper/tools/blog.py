"""
Tool: Blog Manager (v2.2 - Windows Fix)
Description: Professional blogging suite with Drafts, SEO Slugs, RSS, and Tags.
"""
import sqlite3
import time
import uuid
import html
import re
import json
from pathlib import Path
from email.utils import formatdate

META = {
    "name": "Blog Manager",
    "icon": "📝",
    "desc": "Publish articles with rich media & RSS."
}

DB_PATH = Path("tools/blog.db")

# ---------------- DATABASE ----------------

def db():
    """Get database connection context"""
    DB_PATH.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    init_db(c)
    return c

def init_db(c):
    c.execute("""CREATE TABLE IF NOT EXISTS blogs (
        id TEXT PRIMARY KEY, handle TEXT, name TEXT, slug TEXT, 
        description TEXT, created_at INTEGER, 
        UNIQUE(handle, slug)
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS posts (
        id TEXT PRIMARY KEY, blog_id TEXT, title TEXT, content TEXT, 
        slug TEXT, status TEXT DEFAULT 'published',
        published_at INTEGER, updated_at INTEGER,
        excerpt TEXT, tags TEXT DEFAULT '[]', featured_image TEXT,
        created_at INTEGER, views INTEGER DEFAULT 0,
        UNIQUE(blog_id, slug)
    )""")
    c.commit()

# ---------------- COMPATIBILITY LAYER ----------------

def get_blog_conn():
    return db()

def get_blog_by_slug(conn, handle, slug):
    # [FIX] Convert sqlite3.Row to dict immediately so .get() works
    row = conn.execute("SELECT * FROM blogs WHERE handle=? AND slug=?", (handle, slug)).fetchone()
    return dict(row) if row else None

def get_blog_posts(conn, blog_id, limit=50):
    rows = conn.execute("""
        SELECT * FROM posts 
        WHERE blog_id=? AND status='published' 
        ORDER BY published_at DESC LIMIT ?
    """, (blog_id, limit)).fetchall()
    return [dict(r) for r in rows]

def generate_rss_feed(blog, posts):
    return rss_xml_gen(blog, posts)

# ---------------- UTILS ----------------

def slugify(s):
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    s = s.strip('-')
    if not s: return f"post-{uuid.uuid4().hex[:6]}"
    return s

def time_ago(ts):
    if not ts: return "Never"
    seconds = int(time.time() - ts)
    if seconds < 60: return "Just now"
    if seconds < 3600: return f"{seconds//60}m ago"
    if seconds < 86400: return f"{seconds//3600}h ago"
    return f"{seconds//86400}d ago"

def embed_media(text):
    if not text: return ""
    text = html.escape(text) 
    text = re.sub(r'(https?://\S+\.(png|jpg|jpeg|gif|webp))', r'<img src="\1" style="max-width:100%; border-radius:8px; margin:10px 0; display:block;">', text)
    text = re.sub(r'https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=|embed/)|youtu\.be/)([a-zA-Z0-9_-]{11})', r'<div class="vid-wrap"><iframe src="https://www.youtube.com/embed/\1" allowfullscreen></iframe></div>', text)
    text = re.sub(r'https?://open\.spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)(?:\?[^\s&<>]*)?', r'<div style="margin:10px 0"><iframe style="border-radius:12px" src="https://open.spotify.com/embed/\1/\2" width="100%" height="152" frameBorder="0" allow="clipboard-write; encrypted-media; fullscreen; picture-in-picture"></iframe></div>', text)
    return text.replace('\n', '<br>')

def rss_xml_gen(blog, posts):
    # [FIX] Ensure blog is a dict (handles sqlite3.Row safety)
    if blog and not isinstance(blog, dict): blog = dict(blog)

    items = ""
    for p in posts:
        pid = p.get('slug') if p.get('slug') else p['id']
        link = f"https://notifly.cc/c/{blog['handle']}/blog/{blog['slug']}#{pid}"
        
        desc = embed_media(p['content'])
        if p.get('featured_image'):
            desc = f'<img src="{p["featured_image"]}" style="width:100%"><br>' + desc
        if p.get('excerpt'):
            desc = f"<i>{html.escape(p['excerpt'])}</i><hr>" + desc
            
        desc = desc.replace("]]>", "]]]]><![CDATA[>")
        pub_date = formatdate(p.get('published_at') or p['created_at'], usegmt=True)
        
        tags = json.loads(p.get('tags') or '[]')
        category_xml = "".join([f"<category>{html.escape(t)}</category>" for t in tags])

        items += f"""
        <item>
            <title>{html.escape(p['title'] or 'Untitled')}</title>
            <link>{link}</link>
            <description><![CDATA[{desc}]]></description>
            <pubDate>{pub_date}</pubDate>
            <guid>{p['id']}</guid>
            {category_xml}
        </item>
        """
        
    return f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
<title>{html.escape(blog['name'])}</title>
<link>https://notifly.cc/c/{blog['handle']}</link>
<description>{html.escape(blog.get('description') or 'Blog by ' + blog['handle'])}</description>
<lastBuildDate>{formatdate(time.time(), usegmt=True)}</lastBuildDate>
{items}
</channel>
</rss>
"""

# ---------------- UI COMPONENTS ----------------

STYLE = """
<style>
    .blog-app { font-family: sans-serif; max-width: 800px; margin: 0 auto; }
    .blog-card { background: #1a1a1a; border: 1px solid #333; padding: 20px; border-radius: 12px; margin-bottom: 15px; transition: 0.2s; }
    .blog-card:hover { border-color: #eab308; transform: translateY(-2px); }
    .blog-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
    .blog-title { font-size: 18px; font-weight: bold; color: #fff; margin: 0; }
    .blog-meta { color: #888; font-size: 12px; margin-top: 5px; }

    .post-item { border-bottom: 1px solid #222; padding: 15px 0; }
    .post-item:last-child { border: none; }
    
    .status-badge { font-size: 10px; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; margin-left: 10px; }
    .status-published { background: #064e3b; color: #34d399; border: 1px solid #065f46; }
    .status-draft { background: #451a03; color: #fbbf24; border: 1px solid #78350f; }

    .btn { padding: 8px 16px; border-radius: 6px; border: none; font-weight: bold; cursor: pointer; font-size: 13px; }
    .btn-primary { background: #eab308; color: #000; }
    .btn-danger { background: rgba(248, 113, 113, 0.2); color: #f87171; }
    .btn-sec { background: #333; color: #fff; }
    
    .input-group { margin-bottom: 15px; }
    .input-row { display: flex; gap: 10px; }
    .input-field { width: 100%; padding: 12px; background: #0a0a0a; border: 1px solid #333; color: #fff; border-radius: 6px; box-sizing: border-box; }
    .input-field:focus { border-color: #eab308; outline: none; }
    .editor-area { min-height: 300px; font-family: monospace; line-height: 1.5; }
    
    .fade-in { animation: fadeIn 0.3s ease-out; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
</style>
"""

def render_dashboard(handle, blogs):
    create_form = ""
    if len(blogs) < 3:
        create_form = """
        <div class="blog-card">
            <h3 style="margin-top:0; color:#eab308;">＋ Create New Blog</h3>
            <div style="display:flex; gap:10px;">
                <input id="new_bname" class="input-field" placeholder="Blog Name (e.g. Tech Daily)">
                <button class="btn btn-primary" onclick="createBlog()">Create</button>
            </div>
        </div>
        """
    
    blog_list = ""
    for b in blogs:
        blog_list += f"""
        <div class="blog-card" onclick="openBlog('{b['id']}')">
            <div class="blog-header">
                <div>
                    <h3 class="blog-title">{html.escape(b['name'])}</h3>
                    <div class="blog-meta">/{b['slug']} • Created {time_ago(b['created_at'])}</div>
                    <div style="font-size:11px; color:#666; font-style:italic">{html.escape(b['description'] or '')}</div>
                </div>
                <button class="btn btn-danger" onclick="event.stopPropagation(); deleteBlog('{b['id']}')">Delete</button>
            </div>
        </div>
        """
    return f"""{STYLE}<div class="blog-app fade-in"><h2 style='color:#fff; border-bottom:1px solid #333; padding-bottom:15px;'>📝 Blog Manager</h2>{create_form}{blog_list if blogs else '<div style=text-align:center;color:#666;padding:40px>No blogs yet.</div>'}</div>"""

def render_blog_view(handle, blog, posts):
    rss_link = f"https://notifly.cc/c/{handle}/blog/{blog['slug']}.xml"
    
    post_list = ""
    for p in posts:
        status_cls = "status-published" if p['status'] == 'published' else "status-draft"
        status_lbl = "PUBLISHED" if p['status'] == 'published' else "DRAFT"
        
        post_list += f"""
        <div class="post-item">
            <div style="display:flex; justify-content:space-between; align-items:start;">
                <div>
                    <strong style="font-size:16px; color:#fff;">{html.escape(p['title'] or 'Untitled')}</strong>
                    <span class="status-badge {status_cls}">{status_lbl}</span>
                    <div class="blog-meta">Updated {time_ago(p['updated_at'] or p['created_at'])} • {p['views']} views</div>
                </div>
                <div style="display:flex; gap:5px;">
                    <button class="btn btn-sec" onclick="editPost('{p['id']}')">Edit</button>
                    <button class="btn btn-danger" onclick="deletePost('{p['id']}')">Del</button>
                </div>
            </div>
        </div>
        """

    return f"""
    {STYLE}
    <div class="blog-app fade-in">
        <div style="margin-bottom:20px;"><button class="btn btn-sec" onclick="showDash()">← Back</button></div>
        <div class="blog-card" style="border-color:#eab308;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h2 style="margin:0; color:#fff;">{html.escape(blog['name'])}</h2>
                <button class="btn btn-sec" onclick="copyRSS('{rss_link}')">📡 Copy RSS</button>
            </div>
            
            <div style="margin-top:10px; display:flex; gap:10px;">
                <input id="blog_desc" class="input-field" placeholder="Blog subtitle (optional)" value="{html.escape(blog.get('description') or '')}">
                <button class="btn btn-sec" onclick="saveBlogDesc('{blog['id']}')">Save Desc</button>
            </div>

            <div style="margin-top:15px;"><button class="btn btn-primary" style="width:100%; padding:12px;" onclick="newPost('{blog['id']}')">＋ Write New Post</button></div>
        </div>
        <div style="background:#111; padding:20px; border-radius:12px;">
            <h3 style="margin-top:0; color:#ccc;">All Posts</h3>
            {post_list if posts else '<div style="color:#666;">No posts yet.</div>'}
        </div>
    </div>
    """

def render_editor(post):
    is_pub = post.get('status') == 'published'
    chk_pub = 'checked' if is_pub else ''
    
    tags_val = ", ".join(json.loads(post.get('tags') or '[]'))

    return f"""
    {STYLE}
    <div class="blog-app fade-in">
        <div style="display:flex; justify-content:space-between; margin-bottom:15px;">
            <button class="btn btn-sec" onclick="openBlog('{post['blog_id']}')">Cancel</button>
            <div style="color:#eab308; font-weight:bold;">Editing Post</div>
            <button class="btn btn-primary" onclick="savePost('{post['id']}')">Save Changes</button>
        </div>
        
        <div class="input-row">
            <div class="input-group" style="flex:2">
                <label style="display:block; color:#888; font-size:12px;">TITLE</label>
                <input id="p_title" class="input-field" value="{html.escape(post['title'] or '')}">
            </div>
             <div class="input-group" style="flex:1">
                <label style="display:block; color:#888; font-size:12px;">SLUG (URL)</label>
                <input id="p_slug" class="input-field" value="{html.escape(post['slug'] or '')}" placeholder="auto-generated">
            </div>
        </div>

        <div class="input-group">
            <label style="display:block; color:#888; font-size:12px;">FEATURED IMAGE URL (Optional)</label>
            <input id="p_image" class="input-field" value="{html.escape(post.get('featured_image') or '')}" placeholder="https://...">
        </div>

        <div class="input-group">
            <label style="display:block; color:#888; font-size:12px;">TAGS (Comma separated)</label>
            <input id="p_tags" class="input-field" value="{html.escape(tags_val)}" placeholder="tech, tutorial, news">
        </div>

        <div class="input-group">
            <label style="display:block; color:#888; font-size:12px;">EXCERPT (Optional summary)</label>
            <textarea id="p_excerpt" class="input-field" rows="2">{html.escape(post['excerpt'] or '')}</textarea>
        </div>
        
        <div class="input-group">
            <label style="display:block; color:#888; font-size:12px;">CONTENT (HTML + Auto-Embeds)</label>
            <textarea id="p_content" class="input-field editor-area">{html.escape(post['content'] or '')}</textarea>
        </div>
        
        <div style="background:#222; padding:15px; border-radius:8px; display:flex; justify-content:space-between; align-items:center;">
            <label style="color:#fff; font-weight:bold;">
                <input type="checkbox" id="p_status" {chk_pub}> Publish immediately?
            </label>
            <div style="font-size:11px; color:#666;">Uncheck to save as Draft</div>
        </div>
    </div>
    """

# ---------------- SCRIPTS ----------------

SCRIPT = """
<script>
window.api = function(act, data={}) {
    fetch('/api/tier2/exec/toolbox/'+handle, {
        method:'POST',
        body:JSON.stringify({ pin:pin, action:'exec_tool', payload:{ tool_id:'blog', data:Object.assign({sub_action:act}, data) } })
    }).then(r=>r.json()).then(j=> {
        if(j.html) document.getElementById('tb_list').innerHTML = j.html;
        else if(j.reload) runTool('blog','Blog Manager');
        else alert(j.msg || 'Error');
    });
}
window.showDash = () => runTool('blog','Blog Manager');
window.createBlog = () => window.api('create_blog', {name: document.getElementById('new_bname').value});
window.deleteBlog = (id) => confirm('Delete blog?') && window.api('delete_blog', {id:id});
window.openBlog = (id) => window.api('view_blog', {id:id});
window.saveBlogDesc = (bid) => window.api('update_blog_desc', {bid:bid, desc:document.getElementById('blog_desc').value});

window.newPost = (bid) => window.api('create_post', {bid:bid});
window.editPost = (pid) => window.api('edit_post', {pid:pid});
window.deletePost = (pid) => confirm('Delete post?') && window.api('delete_post', {pid:pid});
window.savePost = (pid) => {
    const tagsRaw = document.getElementById('p_tags').value;
    const tagsList = tagsRaw.split(',').map(t => t.trim()).filter(Boolean);

    window.api('update_post', {
        pid:pid, 
        title:document.getElementById('p_title').value,
        slug:document.getElementById('p_slug').value,
        excerpt:document.getElementById('p_excerpt').value,
        content:document.getElementById('p_content').value,
        featured_image:document.getElementById('p_image').value,
        tags:tagsList,
        status:document.getElementById('p_status').checked ? 'published' : 'draft'
    });
};
window.copyRSS = (url) => { navigator.clipboard.writeText(url); alert('RSS Link Copied!'); };
</script>
"""

# ---------------- LOGIC ----------------

def run(conn, handle, payload):
    c = db()
    try:
        act = payload.get("sub_action")
        
        if act == "create_blog":
            name = payload.get("name", "").strip()
            if not name: return {"msg": "Name required"}
            slug = slugify(name)
            if c.execute("SELECT 1 FROM blogs WHERE handle=? AND slug=?", (handle, slug)).fetchone():
                slug = f"{slug}-{uuid.uuid4().hex[:4]}"
            c.execute("INSERT INTO blogs (id,handle,name,slug,created_at) VALUES (?,?,?,?,?)",
                      (uuid.uuid4().hex[:8], handle, name, slug, int(time.time())))
            c.commit()
            return {"reload": True}
        
        if act == "update_blog_desc":
            desc = payload.get("desc", "").strip()[:200]
            c.execute("UPDATE blogs SET description=? WHERE id=?", (desc, payload.get("bid")))
            c.commit()
            return {"reload": True}

        if act == "delete_blog":
            c.execute("DELETE FROM blogs WHERE id=?", (payload.get("id"),))
            c.execute("DELETE FROM posts WHERE blog_id=?", (payload.get("id"),))
            c.commit()
            return {"reload": True}

        if act == "create_post":
            bid = payload.get("bid")
            pid = uuid.uuid4().hex[:8]
            c.execute("INSERT INTO posts (id,blog_id,title,content,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                      (pid, bid, "", "", 'draft', int(time.time()), int(time.time())))
            c.commit()
            post = c.execute("SELECT * FROM posts WHERE id=?", (pid,)).fetchone()
            return {"success": True, "html": render_editor(dict(post)) + SCRIPT}

        if act == "update_post":
            pid = payload.get("pid")
            title = payload.get("title", "").strip()[:200]
            content = payload.get("content", "")
            excerpt = payload.get("excerpt", "")[:300]
            status = payload.get("status", "draft")
            user_slug = payload.get("slug", "").strip()
            featured_image = payload.get("featured_image", "").strip()[:500]
            tags = json.dumps(payload.get("tags", []))
            
            if len(content) > 1_000_000: return {"msg": "Content too large"}

            # Slug Logic
            slug = slugify(user_slug if user_slug else title)
            post_check = c.execute("SELECT blog_id FROM posts WHERE id=?", (pid,)).fetchone()
            if post_check:
                bid = post_check['blog_id']
                exist = c.execute("SELECT 1 FROM posts WHERE blog_id=? AND slug=? AND id!=?", (bid, slug, pid)).fetchone()
                if exist: slug = f"{slug}-{uuid.uuid4().hex[:4]}"

            # Timestamp Logic
            post = c.execute("SELECT status, published_at FROM posts WHERE id=?", (pid,)).fetchone()
            now = int(time.time())
            was_draft = post['status'] == 'draft'
            is_publishing_now = (status == 'published' and was_draft)
            
            if is_publishing_now:
                sql = """UPDATE posts SET title=?, content=?, excerpt=?, slug=?, status=?, 
                       featured_image=?, tags=?, updated_at=?, published_at=? WHERE id=?"""
                args = (title, content, excerpt, slug, status, featured_image, tags, now, now, pid)
            else:
                sql = """UPDATE posts SET title=?, content=?, excerpt=?, slug=?, status=?, 
                       featured_image=?, tags=?, updated_at=? WHERE id=?"""
                args = (title, content, excerpt, slug, status, featured_image, tags, now, pid)

            c.execute(sql, args)
            c.commit()
            
            post = c.execute("SELECT * FROM posts WHERE id=?", (pid,)).fetchone()
            return {"success": True, "html": run(None, handle, {"sub_action": "view_blog", "id": post['blog_id']})['html']}

        if act == "delete_post":
            post = c.execute("SELECT blog_id FROM posts WHERE id=?", (payload.get("pid"),)).fetchone()
            if not post: return {"msg": "Post not found"}
            c.execute("DELETE FROM posts WHERE id=?", (payload.get("pid"),))
            c.commit()
            return {"success": True, "html": run(None, handle, {"sub_action": "view_blog", "id": post['blog_id']})['html']}

        if act == "view_blog":
            bid = payload.get("id")
            blog = c.execute("SELECT * FROM blogs WHERE id=?", (bid,)).fetchone()
            posts = c.execute("SELECT * FROM posts WHERE blog_id=? ORDER BY updated_at DESC", (bid,)).fetchall()
            return {"success": True, "html": render_blog_view(handle, dict(blog), [dict(p) for p in posts]) + SCRIPT}

        if act == "edit_post":
            post = c.execute("SELECT * FROM posts WHERE id=?", (payload.get("pid"),)).fetchone()
            return {"success": True, "html": render_editor(dict(post)) + SCRIPT}

        blogs = c.execute("SELECT * FROM blogs WHERE handle=? ORDER BY created_at DESC", (handle,)).fetchall()
        return {"success": True, "html": render_dashboard(handle, [dict(b) for b in blogs]) + SCRIPT}

    except Exception as e:
        return {"msg": f"Error: {str(e)}"}
    finally:
        c.close()
