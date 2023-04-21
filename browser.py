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

def lex(body):
    out = []
    text = ""
    in_tag = False 
    for c in body:
        if c == "<":
            in_tag = True
            if text: out.append(Text(text))
            text = "" 
        elif c == ">":
            in_angle = False
            out.append(Tag(text))
            text = "" 
        else:
            text += c
    if not in_tag and text:
        out.append(Text(text))
    return out  
   
class Layout:
    def __init__(self, tokens):
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 16
        self.line = []

        for tok in tokens:
            self.token(tok)
        self.flush()

    def token(self, tok):
        if isinstance(tok, Text):
            self.text(tok)
        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4
        elif tok.tag == "br":
            self.flush()
        elif tok.tag == "/p":
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
        tokens = lex(body)
        self.display_list = Layout(tokens).display_list
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
    def __init__(self, text):
        self.text = text

class Tag:
    def __init__(self, tag):
        self.tag = tag

if __name__ == '__main__':
    Browser().load(sys.argv[1])
    tkinter.mainloop()









       