from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        print(tag)
        for attr, value in attrs:
            print(f"-> {attr} > {value}")
    
    def handle_endtag(self, tag):
        pass
        
    def handle_startendtag(self, tag, attrs):
        print(tag)
        for attr, value in attrs:
            print(f"-> {attr} > {value}")
    
    def handle_comment(self, data):
        pass

def main():
    n = int(input())
    html_content = ""
    for _ in range(n):
        html_content += input() + "\n"
    
    parser = MyHTMLParser()
    parser.feed(html_content)

if __name__ == "__main__":
    main()