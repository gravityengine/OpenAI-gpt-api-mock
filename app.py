import tornado.ioloop
import tornado.web
import tornado.httpclient
import json
import time
import asyncio
from urllib.parse import quote

class MainHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Server", "cloudflare")
        self.set_header("CF-Cache-Status", "DYNAMIC")
        self.set_header("Cache-Control", "no-cache, must-revalidate")
        self.set_header("Content-Type", "text/event-stream")
        self.set_header("openai-organization", "gpt4-k2za1m")
        self.set_header("openai-processing-ms", "6")
        self.set_header("openai-version", "2020-10-01")
        self.set_header("x-ratelimit-limit-requests", "200")
        self.set_header("x-ratelimit-limit-tokens", "40000")
        self.set_header("x-ratelimit-remaining-requests", "199")
        self.set_header("x-ratelimit-remaining-tokens", "39974")
        self.set_header("x-ratelimit-reset-requests", "300ms")
        self.set_header("x-ratelimit-reset-tokens", "39ms")
        self.set_header("x-request-id", "16c806d0ddaa815ca25ec84c5887165c")
        self.set_header("access-control-allow-origin", "*")
        self.set_header("alt-svc", 'h3=":443"; ma=86400')
        self.set_header("strict-transport-security", "max-age=15724800; includeSubDomains")
        self.set_header("access-control-allow-origin", "*")
        self.set_header("access-control-allow-headers", "x-requested-with, content-type, authorization")  # added authorization
        self.set_header("access-control-allow-methods", "POST, OPTIONS")
        
    def options(self):
        # no body
        self.set_status(204)
        self.finish()
        
    def check_origin(self, origin):
        return True
        
    async def get_text_from_api(self, spoken):
        http_client = tornado.httpclient.AsyncHTTPClient()
        response = await http_client.fetch(f"https://api.ownthink.com/bot?appid=2f61324232f2f0c481bfec59ecb84bb3&userid=8qM2yRs4&spoken={spoken}")
        data = json.loads(response.body)
        return data['data']['info']['text']

    async def post(self):
        data = tornado.escape.json_decode(self.request.body)
        messages = data['messages']
        stream = data.get('stream', False)

        last_user_message = None
        for message in reversed(messages):
            if message['role'] == 'user':
                last_user_message = message['content']
                break

        if last_user_message is None:
            self.write(json.dumps({'error': 'No user message found'}))
            self.set_status(400)
            return

        text = await self.get_text_from_api(quote(last_user_message))

        current_time = int(time.time())

        if stream:
            self.set_header('content-type', 'text/event-stream')
            self.set_header('cache-control', 'no-cache')
            self.set_header('connection', 'keep-alive')

            messages = []

            for char in text:
                messages.append(
                    {
                        'id': 'chatcmpl-7js4kG4upSmJWwysFKj50JgXUV9ez',
                        'object': 'chat.completion.chunk',
                        'created': current_time,
                        'model': 'gpt-4-32k',
                        'choices': [
                            {
                                'index': 0,
                                'delta': {
                                    'role': 'assistant',
                                    'content': char
                                },
                                'finish_reason': None
                            }
                        ]
                    }
                )

            messages.append(
                {
                    'id': 'chatcmpl-7js4kG4upSmJWwysFKj50JgXUV9ez',
                    'object': 'chat.completion.chunk',
                    'created': current_time,
                    'model': 'gpt-4-32k',
                    'choices': [
                        {
                            'index': 0,
                            'delta': {},
                            'finish_reason': 'stop'
                        }
                    ]
                }
            )

            messages.append("[DONE]")

            for message in messages:
                if isinstance(message, str):
                    self.write(f"data: {message}\n\n")
                else:
                    self.write(f"data: {json.dumps(message)}\n\n")
                await self.flush()
                await asyncio.sleep(0.01)
        else:
            response = {
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "created": current_time,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": text,
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 900,
                    "completion_tokens": 1200,
                    "total_tokens": 2100
                }
            }
            self.write(json.dumps(response))

def make_app():
    return tornado.web.Application([
        (r"/v1/chat/completions", MainHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(5000)
    tornado.ioloop.IOLoop.current().start()
