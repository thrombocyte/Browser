import sys, os, ssl 
import tkinter 
import tkinter.font

#import urllib.parse: helpful ibrary, unused herein 
#url = "http://example.org/index.html"

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100
FONTS = {}


def get_font(size, weight, slant):
    key = (size, weight, slant)
    if key not in FONTS:
        font = tkinter.font.Font(size = size, weight = weight, slant = slant)
        FONTS[key] = font
    return FONTS[key]
    
def request(url):
    #old line: assert url.startswith("http://")
    scheme, url = url.split("://", 1)
    assert scheme in ["http", "https"], \
        "Unknown scheme {}".format(scheme)
    host, path = url.split("/", 1)
    path = "/" + path 
    port = 80 if scheme == "http" else 443
    
    #allow custom ports 
    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)

    import socket 
    #create the socket
    s = socket.socket(
        family = socket.AF_INET,
        type = socket.SOCK_STREAM,
        proto = socket.IPPROTO_TCP
    )
    
    #connect to the internet using correctport
    s.connect((host, port))

    #encrypt the connection using ssl 
    if scheme == "https":
        context = ssl.create_default_context()
        s = context.wrap_socket(s, server_hostname = host)
    
    
    s.send("GET {} HTTP/1.0\r\n".format(path).encode("utf8") + 
        "Host: {}\r\n\r\n".format(host).encode("utf8"))
    
    response = s.makefile("r", encoding = "utf8", newline="\r\n")
    
    statusline = response.readline()
    version, status, explanation = statusline.split(" ", 2)
    assert status == "200", "{}: {}".format(status, explanation)
    
    headers = {}
    while True:
        line = response.readline()
        if line == "\r\n": break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    
    assert "transfer-encoding" not in headers
    assert "content-encoding" not in headers 
    
    body = response.read()
    s.close()
    
    return headers, body 

def print_tree(node, indent = 0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)
   
class HTMLParser:
    SELF_CLOSING_TAGS = ["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"]
    HEAD_TAGS = ["base", "basefont", "bgsound", "noscript", "link", "meta", "title", "style", "script"]

    def __init__(self, body):
        self.body = body 
        self.unfinished = []

    def parse(self):
        text = ""
        in_tag = False 
        for c in self.body:
            if c == "<":
                in_tag = True
                if text: self.add_text(text)
                text = "" 
            elif c == ">":
                in_tag = False
                self.add_tag(text)
                text = "" 
            else:
                text += c
        if not in_tag and text:
            self.add_text(text)
        return self.finish()
    
    def get_attributes(self, text):
        parts = text.split()
        tag = parts[0].lower()
        attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1: -1]
                attributes[key.lower()] = value 
            else: 
                attributes[attrpair.lower()] = ""
        return tag, attributes 
    
    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break

    def add_text(self, text):
        if text.isspace(): return 
        self.implicit_tags(None)
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"): return
        self.implicit_tags(tag) 
        if tag.startswith("/"):
            if len(self.unfinished) == 1: return 
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None 
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)
        

    def finish(self):
        if len(self.unfinished) == 0:
            self.add_tag("html")
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()

class Layout:
    def __init__(self, tokens):
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 16
        self.line = []

        self.recurse(tokens)

    def recurse(self, tree):
        if isinstance(tree, Text):
            self.text(tree)
        else:
            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)



    def open_tag(self, tag):
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "br":
            self.flush()

    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP

    def text(self, tok):
        font = get_font(self.size, self.weight, self.style)

        for word in tok.text.split():
            w = font.measure(word)
            if self.cursor_x + w >= WIDTH-HSTEP:
                self.flush()
            self.line.append((self.cursor_x, word, font))
            self.cursor_x += w + font.measure(" ") 

    def flush(self):
        if not self.line: return  
        metrics = [font.metrics() for x, word, font, in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
        self.cursor_x = HSTEP
        self.line = []
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline  + 1.25 * max_descent 

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.window.title('Reuben Browser')
        self.canvas = tkinter.Canvas(
            self.window, 
            width = WIDTH,
            height = HEIGHT
            
        )
        self.canvas.pack()

        self.scroll = 0
        self.display_list = []
        self.window.bind("<Button-4>", self.scrollup)
        self.window.bind("<Button-5>", self.scrolldown)

    def load(self, url):
        headers, body = request(url)
        self.nodes = HTMLParser(body).parse()
        self.display_list = Layout(self.nodes).display_list
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c, f in self.display_list:
            if y > self.scroll + HEIGHT: continue 
            if y + VSTEP < self.scroll: continue 
            self.canvas.create_text(x, y - self.scroll, text=c, anchor = 'nw', font= f)

    def scrolldown(self, event):
        self.scroll += SCROLL_STEP
        self.draw()

    def scrollup(self, event):
        self.scroll -= SCROLL_STEP
        self.draw()

class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent 

    def __repr__(self):
        return repr(self.text)

class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent

    def __repr__(self):
        return "<" + self.tag + ">"

if __name__ == '__main__':
    Browser().load(sys.argv[1])
    tkinter.mainloop()






       