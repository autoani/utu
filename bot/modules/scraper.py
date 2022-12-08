import cloudscraper
import concurrent.futures
from copy import deepcopy
from re import S, match as rematch, findall, sub as resub, compile as recompile
from asyncio import sleep as asleep
from time import sleep
from urllib.parse import urlparse, unquote
from requests import get as rget, head as rhead
from bs4 import BeautifulSoup, NavigableString, Tag

from telegram import Message
from telegram.ext import CommandHandler
from bot import LOGGER, dispatcher, config_dict, OWNER_ID
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage
from bot.helper.ext_utils.bot_utils import is_paid, is_sudo
from bot.helper.mirror_utils.download_utils.direct_link_generator import rock, try2link, ez4
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException

drive_list = ['drivelinks.in', 'driveroot.in', 'drivesharer.in', 'driveace.in', "drivehub.in"]

def scrapper(update, context):
    user_id_ = update.message.from_user.id
    if config_dict['PAID_SERVICE'] is True:
        if user_id_ != OWNER_ID and not is_sudo(user_id_) and not is_paid(user_id_):
            sendMessage(f"Buy Paid Service to Use this Scrape Feature.", context.bot, update.message)
            return
    message:Message = update.effective_message
    link = None
    if message.reply_to_message: link = message.reply_to_message.text
    else:
        link = message.text.split(' ', 1)
        if len(link) == 2:
            link = link[1]
        else:
            help_msg = "<b>Send link after command:</b>"
            help_msg += f"\n<code>/{BotCommands.ScrapeCommand[0]}" + " {link}" + "</code>\n"
            help_msg += "\n<b>By Replying to Message (Including Link):</b>"
            help_msg += f"\n<code>/{BotCommands.ScrapeCommand[0]}" + " {message}" + "</code>"
            return sendMessage(help_msg, context.bot, update.message)
    try: link = rematch(r"^(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))", link)[0]
    except TypeError: return sendMessage('Not a Valid Link.', context.bot, update)
    links = []
    if "sharespark" in link:
        gd_txt = ""
        res = rget("?action=printpage;".join(link.split('?')))
        soup = BeautifulSoup(res.text, 'html.parser')
        for br in soup.findAll('br'):
            next_s = br.nextSibling
            if not (next_s and isinstance(next_s,NavigableString)):
                continue
            next2_s = next_s.nextSibling
            if next2_s and isinstance(next2_s,Tag) and next2_s.name == 'br':
              if str(next_s).strip():
                 List = next_s.split()
                 if rematch(r'^(480p|720p|1080p)(.+)? Links:\Z', next_s):
                    gd_txt += f'<b>{next_s.replace("Links:", "GDToT Links :")}</b>\n\n'
                 for s in List:
                      ns = resub(r'\(|\)', '', s)
                      if rematch(r'https?://.+\.gdtot\.\S+', ns):
                         r = rget(ns)
                         soup = BeautifulSoup(r.content, "html.parser")
                         title = soup.title
                         gd_txt += f"<code>{(title.text).replace('GDToT | ' , '')}</code>\n{ns}\n\n"
                      elif rematch(r'https?://pastetot\.\S+', ns):
                         nxt = resub(r'\(|\)|(https?://pastetot\.\S+)', '', next_s)
                         gd_txt += f"\n<code>{nxt}</code>\n{ns}\n"
            if len(gd_txt) > 4000:
                sendMessage(gd_txt, context.bot, update.message)
                gd_txt = ""
        if gd_txt != "":
            sendMessage(gd_txt, context.bot, update.message)
    elif "htpmovies" in link and "/exit.php" in link:
        sent = sendMessage('Running scrape. Wait about some secs.', context.bot, update.message)
        prsd = htpmovies(link)
        editMessage(prsd, sent)
    elif "htpmovies" in link:
        sent = sendMessage('Running scrape. Wait about some secs.', context.bot, update.message)
        prsd = ""
        links = []
        res = rget(link)
        soup = BeautifulSoup(res.text, 'html.parser')
        x = soup.select('a[href^="/exit.php?url="]')
        y = soup.select('h5')
        z = unquote(link.split('/')[-2]).split('-')[0] if link.endswith('/') else unquote(link.split('/')[-1]).split('-')[0]

        for a in x:
            links.append(a['href'])
            prsd = f"Total Links Found : {len(links)}\n\n"
        editMessage(prsd, sent)
        msdcnt = -1
        for b in y:
            if str(b.string).lower().startswith(z.lower()):
                msdcnt += 1
                url = f"https://htpmovies.lol"+links[msdcnt]
                prsd += f"{msdcnt+1}. <b>{b.string}</b>\n{htpmovies(url)}\n\n"
                editMessage(prsd, sent)
                asleep(5)
                if len(prsd) > 4000:
                    sent = sendMessage("<i>Scrapping More...</i>", context.bot, update.message)
                    prsd = ""
    elif "teluguflix" in link:
        sent = sendMessage('Running Scrape ...', context.bot, update.message)
        gd_txt = ""
        r = rget(link)
        soup = BeautifulSoup (r.text, "html.parser")
        links = soup.select('a[href*="gdtot"]')
        gd_txt = f"Total Links Found : {len(links)}\n\n"
        editMessage(gd_txt, sent)
        for no, link in enumerate(links, start=1):
            gdlk = link['href']
            t = rget(gdlk)
            soupt = BeautifulSoup(t.text, "html.parser")
            title = soupt.select('meta[property^="og:description"]')
            gd_txt += f"{no}. <code>{(title[0]['content']).replace('Download ' , '')}</code>\n{gdlk}\n\n"
            editMessage(gd_txt, sent)
            asleep(1.5)
            if len(gd_txt) > 4000:
                sent = sendMessage("<i>Running More Scrape ...</i>", context.bot, update.message)
                gd_txt = ""
    elif "cinevood" in link:
        prsd = ""
        links = []
        res = rget(link)
        soup = BeautifulSoup(res.text, 'html.parser')
        x = soup.select('a[href^="https://kolop.icu/file"]')
        for a in x:
            links.append(a['href'])
        for o in links:
            res = rget(o)
            soup = BeautifulSoup(res.content, "html.parser")
            title = soup.title.string
            reftxt = resub(r'Kolop \| ', '', title)
            prsd += f'{reftxt}\n{o}\n\n'
            if len(prsd) > 4000:
                sendMessage(prsd, context.bot, update.message)
                prsd = ""
        if prsd != "":
            sendMessage(prsd, context.bot, update.message)
    elif "atishmkv" in link:
        prsd = ""
        links = []
        res = rget(link)
        soup = BeautifulSoup(res.text, 'html.parser')
        x = soup.select('a[href^="https://gdflix.top/file"]')
        for a in x:
            links.append(a['href'])
        for o in links:
            prsd += o + '\n\n'
            if len(prsd) > 4000:
                sendMessage(prsd, context.bot, update.message)
                
                prsd = ""
        if prsd != "":
            sendMessage(prsd, context.bot, update.message)
    elif "taemovies" in link:
        sent = sendMessage('Running Scrape ...', context.bot, update.message)
        gd_txt, no = "", 0
        r = rget(link)
        soup = BeautifulSoup (r.text, "html.parser")
        links = soup.select('a[href*="shortingly"]')
        gd_txt = f"Total Links Found : {len(links)}\n\n"
        editMessage(gd_txt, sent)
        for a in links:
            glink = rock(a["href"]) 
            t = rget(glink)
            soupt = BeautifulSoup(t.text, "html.parser")
            title = soupt.select('meta[property^="og:description"]')
            no += 1
            gd_txt += f"{no}. {(title[0]['content']).replace('Download ' , '')}\n{glink}\n\n"
            editMessage(gd_txt, sent)
            if len(gd_txt) > 4000:
                sent = sendMessage("<i>Running More Scrape ...</i>", context.bot, update.message)
                gd_txt = ""
    elif "toonworld4all" in link:
        sent = sendMessage('Running Scrape ...', context.bot, update.message)
        gd_txt, no = "", 0
        r = rget(link)
        soup = BeautifulSoup(r.text, "html.parser")
        links = soup.select('a[href*="redirect/main.php?"]')
        for a in links:
            down = rget(a['href'], stream=True, allow_redirects=False)
            link = down.headers["location"]
            glink = rock(link)
            if glink and "gdtot" in glink:
                t = rget(glink)
                soupt = BeautifulSoup(t.text, "html.parser")
                title = soupt.select('meta[property^="og:description"]')
                no += 1
                gd_txt += f"{no}. {(title[0]['content']).replace('Download ' , '')}\n{glink}\n\n"
                editMessage(gd_txt, sent)
                if len(gd_txt) > 4000:
                    sent = sendMessage("<i>Running More Scrape ...</i>", context.bot, update.message)
                    gd_txt = ""
    elif "moviesmod" in link:
        sent = sendMessage('Running Scrape ...', context.bot, update.message)
        gd_txt, no, to_edit = "", 0, False
        rep = rget(link)
        soup = BeautifulSoup(rep.text, 'html.parser')
        links = soup.select("a[rel='noopener nofollow external noreferrer']")
        gd_txt = f"Total Links Found : {len(links)}\n"
        for l in links:
            gd_txt += f"\n{(l.text).replace('Download Links', '🏷 Download Links')} :\n"
            scrapper = cloudscraper.create_scraper(allow_brotli=False)
            res = scrapper.get(l['href'])
            nsoup = BeautifulSoup(res.text, 'html.parser')
            for ll in nsoup.select('a[href]'):
                for url in drive_list:
                    if url in ll['href']:
                        nl = (rget(ll['href']).text).split('"')[1]
                        gd_txt += f"https://{url}{nl}\n"
                if 'urlflix.xyz' in ll['href']:
                    resp = rget(ll['href'])
                    ssoup = BeautifulSoup(resp.text, 'html.parser')
                    atag = ssoup.select('div[id="text-url"] > a[href]')
                    for ref in atag:
                        gd_txt += ref['href'] + '\n'
                if len(gd_txt) > 4000:
                    asleep(2.5)
                    editMessage(gd_txt, sent)
                    to_edit = True
                    gd_txt = ""
        if gd_txt != "" and to_edit:
            sendMessage(gd_txt, context.bot, update.message)
        elif gd_txt!= "":
            editMessage(gd_txt, sent)
    elif "skymovieshd" in link:
        sent = sendMessage('Running Scrape ...', context.bot, update.message)
        gd_txt = ""
        res = rget(link, allow_redirects=False)
        soup = BeautifulSoup(res.text, 'html.parser')
        a = soup.select('a[href^="https://howblogs.xyz"]')
        t = soup.select('div[class^="Robiul"]')
        gd_txt += f"<i>{t[-1].text.replace('Download ', '')}</i>\n\n"
        gd_txt += f"<b>{a[0].text} :</b> \n"
        nres = rget(a[0]['href'], allow_redirects=False)
        nsoup = BeautifulSoup(nres.text, 'html.parser')
        atag = nsoup.select('div[class="cotent-box"] > a[href]')
        for no, link in enumerate(atag, start=1):
            gd_txt += f"{no}. {link['href']}\n"
        editMessage(gd_txt, sent)
    elif "animekaizoku" in link:
        sent = sendMessage('Running Scrape ... Coming Soon...', context.bot, update.message)
        global post_id
        DDL_REGEX = recompile(r"DDL\(([^),]+)\, (([^),]+)), (([^),]+)), (([^),]+))\)")
        POST_ID_REGEX =  recompile(r'"postId":"(\d+)"')
        try: website_html = rget(url).text
        except: editMessage("Please provide the correct episode link of animekaizoku", sent); return
        try:
            post_id = POST_ID_REGEX.search(website_html).group(0).split(":")[1].split('"')[1]
            payload_data_matches = DDL_REGEX.finditer(website_html)
        except: editMessage("Something Went wrong !!", sent); return

        for match in payload_data_matches:
            payload_data = match.group(0).split("DDL(")[1].replace(")", "").split(",")
            payload = {
               "action" : "DDL",
               "post_id": post_id,
               "div_id" : payload_data[0].strip(),
               "tab_id" : payload_data[1].strip(),
               "num"    : payload_data[2].strip(),
               "folder" : payload_data[3].strip(),
            }
            del payload["num"]     
            link_types = "DDL" if payload["tab_id"] == "2" else "WORKER" if payload["tab_id"] == "4" else "GDRIVE"
            response = rpost("https://animekaizoku.com/wp-admin/admin-ajax.php",headers=headers, data=payload)
            soup = BeautifulSoup(response.text, "html.parser")  
            downloadbutton = soup.find_all(class_="downloadbutton")
            print(f"Now Scrapping {link_types} Links .....")

            with concurrent.futures.ThreadPoolExecutor() as executor:
                for button in downloadbutton:
                    if button.text == "Patches": pass
                    else:
                        dict_key = button.text.strip()
                        data_dict[dict_key] = []
                        executor.submit(looper, dict_key, str(button))
            main_dict[link_types] = deepcopy(data_dict)
            data_dict.clear()
        #dictionary_decrypter()
    elif "animeremux" in link:
        sent = sendMessage('Running Scrape ...', context.bot, update.message)
        gd_txt, no = "", 0
        r = rget(link)
        soup = BeautifulSoup (r.text, "html.parser")
        links = soup.select('a[href*="urlshortx.com"]')
        gd_txt = f"Total Links Found : {len(links)}\n\n"
        editMessage(gd_txt, sent)
        ptime = 0
        for a in links:
            link = a["href"]
            x = link.split("url=")[-1]
            t = rget(x)
            soupt = BeautifulSoup(t.text, "html.parser")
            title = soupt.title
            no += 1
            gd_txt += f"{no}. {title.text}\n{x}\n\n"
            ptime += 1
            if ptime == 3:
                ptime = 0
                asleep(5)
                editMessage(gd_txt, sent)
                if len(gd_txt) > 4000:
                    sent = sendMessage("<i>Running More Scrape ...</i>", context.bot, update.message)
                    gd_txt = ""
    elif "olamovies" in link:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': link,
            'Alt-Used': 'olamovies.ink',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
        }
        sent = sendMessage('Running Scrape ...', context.bot, update.message)
        gd_txt, no = "", 0
        client = cloudscraper.create_scraper()
        res = client.get(link)
        soup = BeautifulSoup(res.text,"html.parser")
        soup = soup.findAll("div", class_="wp-block-button")
   
        outlist = []
        for ele in soup:
            outlist.append(ele.find("a").get("href"))
        slist = []
        gd_txt = f"Total Links Found : {len(outlist)}\n\n"
        editMessage(gd_txt, sent)
        for ele in outlist:
            try:
                key = ele.split("?key=")[1].split("&id=")[0].replace("%2B","+").replace("%3D","=").replace("%2F","/")
                id = ele.split("&id=")[1]
            except:
                continue
            soup = "None"
            url = f"https://olamovies.wtf/download/&key={key}&id={id}"
            while 'rocklinks.net' not in soup and "try2link.com" not in soup and "ez4short.com" not in soup:
                res = client.get("https://olamovies.ink/download/", params={ 'key': key, 'id': id}, headers=headers)
                soup = (res.text).split('url = "')[-1].split('";')[0]
                if soup != "":
                    if "try2link.com" in soup:
                        final = try2link(soup)
                    elif 'rocklinks.net' in soup:
                        final = rock(soup)
                    elif "ez4short.com" in soup:
                        final = ez4(soup)
                    if "try2link.com" in soup or 'rocklinks.net' in soup or "ez4short.com" in soup:
                        t = client.get(final)
                        soupt = BeautifulSoup(t.text, "html.parser")
                        title = soupt.select('meta[property^="og:description"]')
                        no += 1
                        gd_txt += f"{no}. {(title[0]['content']).replace('Download ' , '')}\n{final}\n\n"
                        editMessage(gd_txt, sent)
                        if len(gd_txt) > 4000:
                            sent = sendMessage("<i>Running More Scrape ...</i>", context.bot, update.message)
                            gd_txt = ""
    else:
        res = rget(link)
        soup = BeautifulSoup(res.text, 'html.parser')
        mystx = soup.select(r'a[href^="magnet:?xt=urn:btih:"]')
        for hy in mystx:
            links.append(hy['href'])
        for txt in links:
            sendMessage(txt, context.bot, update.message)

def htpmovies(link):
    client = cloudscraper.create_scraper(allow_brotli=False)
    r = client.get(link, allow_redirects=True).text
    j = r.split('("')[-1]
    url = j.split('")')[0]
    param = url.split("/")[-1]
    DOMAIN = "https://go.theforyou.in"
    final_url = f"{DOMAIN}/{param}"
    resp = client.get(final_url)
    soup = BeautifulSoup(resp.content, "html.parser")    
    try: inputs = soup.find(id="go-link").find_all(name="input")
    except: return "Incorrect Link"
    data = { input.get('name'): input.get('value') for input in inputs }
    h = { "x-requested-with": "XMLHttpRequest" }
    sleep(10)
    r = client.post(f"{DOMAIN}/links/go", data=data, headers=h)
    try:
        return r.json()['url']
    except: return "Something went Wrong !!"
        
srp_handler = CommandHandler(BotCommands.ScrapeCommand, scrapper,
                            filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)

dispatcher.add_handler(srp_handler)
