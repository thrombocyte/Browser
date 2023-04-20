import sys, os, ssl 
import tkinter 
#import urllib.parse: helpful ibrary, unused herein 
#url = "http://example.org/index.html"

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100



    
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
    in_angle = False 
    text = ""
    for c in body:
        if c == "<":
            in_angle = True 
        elif c == ">":
            in_angle = False 
        elif not in_angle:
            text += c
    return text 
   
def layout(text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x >= WIDTH-HSTEP:
            cursor_x = HSTEP
            cursor_y += VSTEP
    
    return display_list 


class Browser:

    def __init__(self):
        self.window = tkinter.Tk()
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
        text = lex(body)
        self.display_list = layout(text)
        self.draw()


    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT: continue 
            if y + VSTEP < self.scroll: continue 
            self.canvas.create_text(x, y - self.scroll, text=c)



    def scrolldown(self, event):
        self.scroll += SCROLL_STEP
        self.draw()

    def scrollup(self, event):
        self.scroll -= SCROLL_STEP
        self.draw()







if __name__ == '__main__':
    Browser().load(sys.argv[1])
    tkinter.mainloop()









       