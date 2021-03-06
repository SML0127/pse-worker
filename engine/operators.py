import string
import time
import subprocess
import traceback
import random

from lxml import etree
from lxml import html
from amazoncaptcha import AmazonCaptcha
from selenium.common.exceptions import TimeoutException, WebDriverException, InvalidSessionIdException

from util.pse_errors import *
from urllib.parse import urlparse

from functools import partial
print_flushed = partial(print, flush=True)


def post_notification_to_slack(msg, url):
    try:
        #subprocess.Popen("curl -X POST -H 'Content-type: application/json' --data '{\"text\":\"" + str(msg).replace('"',"'") + "\"}' " + url + " &> /dev/null", shell=True)
        print("Notificatino disabled")
    except:
        print(str(traceback.format_exc()))
        pass


class GlovalVariable():

    def __init__(self):
        self.msg = []
        self.err_msg = []
        self.results = {}
        self.web_mgr = None
        self.graph_mgr = None
        self.task_url = None
        self.task_zipcode_url = None
        self.task_id = None
        self.exec_id = None
        self.profiling_info = {}
        self.stack_nodes = []
        self.stack_indices = []

    def append_msg(self, msg):
        self.msg.append(msg)

    def append_err_msg(self, msg):
        self.err_msg.append(msg)

    def get_msg(self):
        return "\n".join(self.msg)

    def get_err_msg(self):
        return "\n".join(self.err_msg)


class BaseOperator():

    def __init__(self):
        self.props = {}
        self.operators = []
        pass

    def __str__(self):
        print_flushed(__class__.__name__)

    def __repr__(self):
        pass

    def before(self, gvar):
        pass

    def after(self, gvar):
        pass

    def run(self, gvar):
        self.before(gvar)
        for op in self.operators:
            op.run(gvar)
        self.after(gvar)

    def rollback(self, gvar):
        pass

    def set_query(self, query, stack_indices, indices):
        indices = indices.split(',') if len(indices) > 0 else []
        return query % (tuple(list(map(lambda x: stack_indices[int(x)] + 1, indices))))


selenium_chrome_erros = ['StaleElementReferenceException',
                         'WebDriverException', 'TimeoutException']


class BFSIterator(BaseOperator):

    def check_captcha(self, url, gvar):
        try:
            print_flushed("@@@@@@@@ Check captcha (amazon)")
            chaptcha_xpath = '//input[@id=\'captchacharacters\']'  # for amazon
            check_chaptcha = gvar.web_mgr.get_elements_by_selenium_(
                chaptcha_xpath)
            cnt = 0
            max_cnt = 4
            while(len(check_chaptcha) != 0):
                cnt = cnt + 1
                print_flushed('Captcha check cnt: ', cnt)
                link = gvar.web_mgr.get_value_by_selenium(
                    '//form[@action="/errors/validateCaptcha"]//img', 'src')
                print_flushed('Captcha image link = {}'.format(link))
                captcha = AmazonCaptcha.fromlink(link)
                solution = captcha.solve()
                print_flushed('String in image = {}'.format(solution))
                gvar.web_mgr.send_keys_to_elements(
                    '//input[@id="captchacharacters"]', solution)
                gvar.web_mgr.click_elements('//button')
                time.sleep(3)
                gvar.web_mgr.load(url)
                check_chaptcha = gvar.web_mgr.get_elements_by_selenium_(
                    chaptcha_xpath)
                if cnt >= max_cnt:
                    raise
        except:
            print_flushed(str(traceback.format_exc()))
            raise

    def check_captcha_rakuten(self, gvar):
        try:
            print_flushed("@@@@@@@@ Check is blocked (rakuten)")
            chaptcha_xpath = '//body[contains(text(),\'Reference\')]'
            print_flushed("Taksid: {}".format(gvar.task_id))
            fname = '/home/pse/PSE-engine/htmls/%s.html' % str(gvar.task_id)
            gvar.web_mgr.store_page_source(fname)
            if gvar.web_mgr.get_html() == '<html><head></head><body></body></html>':
                print_flushed(gvar.web_mgr.get_html())
            check_chaptcha = gvar.web_mgr.get_elements_by_selenium_(
                chaptcha_xpath)
            sleep_time = 10
            while(len(check_chaptcha) != 0 or gvar.web_mgr.get_html() == '<html><head></head><body></body></html>'):
                print_flushed('@@@@@ Restart chrome')
                gvar.web_mgr.restart(sleep_time)
                gvar.web_mgr.load(gvar.task_url)
                #gvar.graph_mgr.insert_node_property(gvar.stack_nodes[-1], 'url', gvar.task_url)
                gvar.web_mgr.wait_loading()
                time.sleep(self.props.get('delay', 0))
                sleep_time += 0
                if gvar.task_url != gvar.web_mgr.get_current_url():
                    time.sleep(5)
                check_chaptcha = gvar.web_mgr.get_elements_by_selenium_(
                    chaptcha_xpath)
        except:
            raise

    def run(self, gvar):

        op_start = time.time()
        # Set up before running sub operators
        err_cnt = 0
        err_op_name = "BFSIterator"
        while True:
            print_flushed(
                '@@@@@ Set up before running sub operators in BFSIterator')
            try:
                op_name = "BFSIterator"
                op_id = self.props['id']
                parent_node_id = self.props.get('parent_node_id', 0)
                label = self.props['label']

                print_flushed("@@@@@@@@@@ task url:", gvar.task_url)

                if gvar.task_zipcode_url is not None:
                    print_flushed("@@@@@@@@@@ input zipcode:",
                                  gvar.task_zipcode_url)

                src_url = urlparse(gvar.task_url).netloc
                print_flushed("@@@@@@@@@@ src_url:", src_url)

                node_id = gvar.graph_mgr.create_node(
                    gvar.task_id, parent_node_id, label)
                gvar.stack_nodes.append(node_id)
                gvar.stack_indices.append(0)
                gvar.graph_mgr.insert_node_property(
                    gvar.stack_nodes[-1], 'url', gvar.task_url)

                if 'amazon.de' in src_url:
                    gvar.web_mgr.load(gvar.task_url)
                    self.check_captcha(gvar.task_url, gvar)
                    gvar.web_mgr.load(gvar.task_url)
                    time.sleep(5)
                    self.check_captcha(gvar.task_url, gvar)
                    cnt = 0
                    while True:
                        cnt = cnt + 1
                        try:
                            site_zipcode = gvar.web_mgr.get_value_by_selenium(
                                '//*[@id="glow-ingress-line2"]', "alltext")
                            print_flushed('Zipcode: ', site_zipcode)
                            if site_zipcode is None:
                                self.check_captcha(
                                    gvar.task_url, gvar)
                                site_zipcode = gvar.web_mgr.get_value_by_selenium(
                                    '//*[@id="glow-ingress-line2"]', "alltext")
                            if '60598' in site_zipcode:
                                break
                            if '60598' not in site_zipcode:
                                print_flushed(
                                    'Change Zipcode')
                                gvar.web_mgr.click_elements(
                                    '//*[@id="nav-global-location-data-modal-action"]')
                                time.sleep(2)
                                gvar.web_mgr.send_keys_to_elements(
                                    '//*[@id="GLUXZipUpdateInput"]', '60598')
                                time.sleep(2)
                                gvar.web_mgr.click_elements(
                                    '//*[@id="GLUXZipInputSection"]/div[2]')
                                time.sleep(2)
                                gvar.web_mgr.click_elements(
                                    '//div[@class="a-popover-footer"]//button')
                                time.sleep(2)
                                gvar.web_mgr.click_elements(
                                    '//div[@class="a-popover-footer"]//input')
                                time.sleep(2)
                                gvar.web_mgr.load(gvar.task_url)
                                self.check_captcha(gvar.task_url, gvar)
                                site_zipcode = gvar.web_mgr.get_value_by_selenium(
                                    '//*[@id="glow-ingress-line2"]', "alltext")
                                print_flushed(
                                    'Zipcode: ', site_zipcode)
                        except:
                            pass

                # elif 'amazon.com' in src_url:
                elif 'amazon.com' in src_url:
                    gvar.web_mgr.load(gvar.task_url)
                    self.check_captcha(gvar.task_url, gvar)
                    gvar.web_mgr.load(gvar.task_url)
                    time.sleep(5)
                    self.check_captcha(gvar.task_url, gvar)
                    cnt = 0
                    while True:
                        cnt = cnt + 1
                        try:
                            site_zipcode = gvar.web_mgr.get_value_by_selenium(
                                '//*[@id="glow-ingress-line2"]', "alltext")
                            print_flushed('Zipcode: ', site_zipcode)
                            if site_zipcode is None:
                                self.check_captcha(
                                    gvar.task_url, gvar)
                                site_zipcode = gvar.web_mgr.get_value_by_selenium(
                                    '//*[@id="glow-ingress-line2"]', "alltext")
                            if '94024' in site_zipcode:
                                break
                            if '94024' not in site_zipcode:
                                print_flushed(
                                    'Change Zipcode')
                                gvar.web_mgr.click_elements(
                                    '//*[@id="nav-global-location-data-modal-action"]')
                                time.sleep(2)
                                gvar.web_mgr.send_keys_to_elements(
                                    '//*[@id="GLUXZipUpdateInput"]', '94024')
                                time.sleep(2)
                                gvar.web_mgr.click_elements(
                                    '//*[@id="GLUXZipInputSection"]/div[2]')
                                time.sleep(2)
                                gvar.web_mgr.click_elements(
                                    '//div[@class="a-popover-footer"]//button')
                                time.sleep(2)
                                gvar.web_mgr.click_elements(
                                    '//div[@class="a-popover-footer"]//input')
                                time.sleep(2)
                                gvar.web_mgr.load(gvar.task_url)
                                self.check_captcha(gvar.task_url, gvar)
                                site_zipcode = gvar.web_mgr.get_value_by_selenium(
                                    '//*[@id="glow-ingress-line2"]', "alltext")
                                print_flushed(
                                    'Zipcode: ', site_zipcode)
                        except:
                            pass

                elif 'amazon.co.uk' in src_url:
                    gvar.web_mgr.load(gvar.task_url)
                    self.check_captcha(gvar.task_url, gvar)
                    gvar.web_mgr.load(gvar.task_url)
                    time.sleep(5)
                    self.check_captcha(gvar.task_url, gvar)
                    cnt = 0
                    while True:
                        cnt = cnt + 1
                        try:
                            site_zipcode = gvar.web_mgr.get_value_by_selenium(
                                '//*[@id="glow-ingress-line2"]', "alltext")
                            print_flushed('Zipcode: ', site_zipcode)
                            if site_zipcode is None:
                                self.check_captcha(
                                    gvar.task_url, gvar)
                                site_zipcode = gvar.web_mgr.get_value_by_selenium(
                                    '//*[@id="glow-ingress-line2"]', "alltext")
                            if 'TW13' in site_zipcode:
                                break
                            if 'TW13' not in site_zipcode:
                                print_flushed(
                                    'Change Zipcode')
                                gvar.web_mgr.click_elements(
                                    '//*[@id="nav-global-location-data-modal-action"]')
                                time.sleep(2)
                                gvar.web_mgr.send_keys_to_elements(
                                    '//*[@id="GLUXZipUpdateInput"]', 'TW13 6DH')
                                time.sleep(2)
                                gvar.web_mgr.click_elements(
                                    '//*[@id="GLUXZipInputSection"]/div[2]')
                                time.sleep(2)
                                gvar.web_mgr.click_elements(
                                    '//div[@class="a-popover-footer"]//button')
                                time.sleep(2)
                                gvar.web_mgr.click_elements(
                                    '//div[@class="a-popover-footer"]//input')
                                time.sleep(2)
                                gvar.web_mgr.load(gvar.task_url)
                                self.check_captcha(gvar.task_url, gvar)
                                site_zipcode = gvar.web_mgr.get_value_by_selenium(
                                    '//*[@id="glow-ingress-line2"]', "alltext")
                                print_flushed(
                                    'Zipcode: ', site_zipcode)
                        except:
                            pass

                else:
                    gvar.web_mgr.load(gvar.task_url)
                    if 'rakuten' in src_url:
                        self.check_captcha_rakuten(gvar)
                #######################################

                gvar.web_mgr.build_lxml_tree()
                time.sleep(5)
                # check invalid page
                if 'amazon' in src_url:
                    print_flushed("@@@@@@@@@@ Check invalid page (amazon)")
                    invalid_page_xpath = "//img[@alt='Dogs of Amazon'] | //span[contains(@id,'priceblock_') and contains(text(),'-')]"
                    is_invalid_page = gvar.web_mgr.get_elements_by_lxml_(
                        invalid_page_xpath)
                    if len(is_invalid_page) != 0:
                        print_flushed("@@@@@@ Invalid page")
                        #gvar.profiling_info[op_id] = {'invalid': True}
                        gvar.profiling_info['invalid'] = True
                        raise InvalidPageError

                elif 'jomashop' in src_url:
                    wrong_to_rendering_xpath = "//div[@id='react-top-error-boundary'] | //*[contains(text(),'Unable to fetch data')] | //*[contains(text(),'Something went wrong')] | //div[@classname='splash-screen'] | //*[contains(text(),'Data Fetch Error')]"
                    render_cnt = 0
                    max_render_cnt = 5
                    while True:
                        print_flushed(
                            "@@@@@@@@@@ Check Wrong to rendering page (jomashop)")
                        wrong_to_rendering_page = gvar.web_mgr.get_elements_by_lxml_(
                            wrong_to_rendering_xpath)
                        if len(wrong_to_rendering_page) != 0:
                            render_cnt = render_cnt + 1
                            if render_cnt >= max_render_cnt:
                                break
                            else:
                                gvar.web_mgr.load(gvar.task_url)
                                time.sleep(5)
                                gvar.web_mgr.build_lxml_tree()
                        else:
                            break

                    print_flushed("@@@@@@@@@@ Check invalid page (jomashop)")
                    #invalid_page_xpath = "//div[@class='image-404'] | //div[@class='product-buttons']//span[contains(text(),'OUT OF STOCK')] | //div[contains(text(),'Sold Out')] | //span[contains(text(),'Ships In')] | //span[contains(text(),'Contact us for')] | //span[contains(text(),'Ships in')] "
                    invalid_page_xpath = "//div[@class='product-buttons']//span[contains(text(),'OUT OF STOCK')] | //div[contains(text(),'Sold Out')] | //span[contains(text(),'Ships In')] | //span[contains(text(),'Contact us for')] | //span[contains(text(),'Ships in')] "
                    invalid_page_xpath = "//div[@class='image-404'] | //*[text()='Unable to fetch data']"
                    is_invalid_page = gvar.web_mgr.get_elements_by_lxml_(
                        invalid_page_xpath)
                    if len(is_invalid_page) != 0:
                        print_flushed("@@@@@@ Invalid page")
                        #gvar.profiling_info[op_id] = {'invalid': True}
                        gvar.profiling_info['invalid'] = True
                        raise InvalidPageError

                elif 'zalando' in src_url:
                    print_flushed("@@@@@@@@@@ Check invalid page (zalando)")
                    invalid_page_xpath = "//h2[contains(text(),'Out of stock')] | //h1[contains(text(),'find this page')]"
                    is_invalid_page = gvar.web_mgr.get_elements_by_lxml_(
                        invalid_page_xpath)
                    if len(is_invalid_page) != 0:
                        print_flushed("@@@@@@ Invalid page")
                        #gvar.profiling_info[op_id] = {'invalid': True}
                        gvar.profiling_info['invalid'] = True
                        raise InvalidPageError

                if 'query' in self.props:
                    print_flushed(
                        "@@@@@@@@@@ Check invalid page or failure using input xpath in BFSIterator")
                    is_invalid_input = gvar.web_mgr.get_elements_by_lxml_(
                        self.props['query'])
                    if len(is_invalid_input) == 0:
                        if 'is_detail' not in self.props:
                            print_flushed(
                                "@@@@@@@@@@ Not Detail page, set as a failure")
                            gvar.profiling_info['check_xpath_error'] = True
                            raise CheckXpathError
                        else:
                            print_flushed(
                                "@@@@@@@@@@ Detail page, set as a invalid page")
                            raise CheckXpathError
                #######################################

                if self.props.get('btn_query', '') != '' and int(self.props['page_id']) != 1:
                    res = gvar.web_mgr.get_value_by_lxml_strong(
                        self.props['btn_query'], 'alltext')
                    print_flushed('@@@@@@@@@@ btn cur :', res)
                    print_flushed(self.props['page_id'])

                    if str(self.props['page_id']) not in res:
                        print_flushed(
                            '@@@@@@@@@@ page number in button != page number in url')
                        gvar.profiling_info['btn_num_error'] = True
                        raise BtnNumError
                gvar.graph_mgr.insert_node_property(
                    gvar.stack_nodes[-1], 'html', gvar.web_mgr.get_html())

                for op in self.operators:
                    op_name = op.props['name']
                    err_op_name = op_name
                    op.run(gvar)

                op_time = time.time() - op_start
                gvar.profiling_info[op_id] = {'op_time': op_time}
                break

            except Exception as e:
                print_flushed(e.__class__.__name__)
                if e.__class__.__name__ == 'BtnNumError':
                    try:
                        fname = '/home/pse/PSE-engine/htmls/%s.html' % str(
                            gvar.task_id)
                        gvar.web_mgr.store_page_source(fname)
                        print_flushed("error html:", fname)
                    except:
                        print_flushed("Fail to dump html")
                        pass
                    err_msg = '================================ CRAWLING NOTIFICATION ============================== \n'
                    err_msg += 'In summary page pagination, button number in URL and element are different.\nPlease check web page and xpath rule\n\nURL: {}\nXpath rule: {}\n\n'.format(
                        str(gvar.task_url), str(self.props['btn_query']).replace("'", '"'))
                    url = gvar.graph_mgr.get_slack_url()
                    post_notification_to_slack(err_msg, url)
                    err_msg = '================================ MESSAGE ============================== \n'
                    err_msg += 'In summary page pagination, button number in URL and element are different.\nPlease check web page and xpath rule\n\nURL: {}\nXpath rule: {}\n\n'.format(
                        str(gvar.task_url), str(self.props['btn_query']).replace("'", '"'))
                    err_msg += '================================ Opeartor ==================================\n'
                    err_msg += err_op_name + ' \n\n'
                    err_msg += '================================ STACK TRACE ============================== \n' + \
                        str(traceback.format_exc())
                    gvar.graph_mgr.log_err_msg_of_task(gvar.task_id, err_msg)
                    raise
                elif e.__class__.__name__ == 'NoneDetailPageError':
                    try:
                        fname = '/home/pse/PSE-engine/htmls/%s.html' % str(
                            gvar.task_id)
                        gvar.web_mgr.store_page_source(fname)
                        print_flushed("error html:", fname)
                    except:
                        print_flushed("Fail to dump html")
                        pass
                    err_msg = '================================ CRAWLING NOTIFICATION ============================== \n'
                    err_msg += 'In summary page pagination, there is no detail page in web page.\n Please check web page and xpath rule \n\nURL: {}\nXPath rule: {}\n\n'.format(
                        str(gvar.task_url), str(e.xpath).replace("'", '"'))
                    url = gvar.graph_mgr.get_slack_url()
                    post_notification_to_slack(err_msg, url)
                    err_msg = '================================ MESSAGE ============================== \n'
                    err_msg += 'In summary page pagination, there is no detail page in web page.\n Please check web page and xpath rule \n\nURL: {}\nXPath rule: {}\n\n'.format(
                        str(gvar.task_url), str(e.xpath).replace("'", '"'))
                    err_msg += '================================ Opeartor ==================================\n'
                    err_msg += 'Expander \n\n'
                    err_msg += '================================ STACK TRACE ============================== \n' + \
                        str(traceback.format_exc())
                    gvar.graph_mgr.log_err_msg_of_task(gvar.task_id, err_msg)
                    raise
                elif e.__class__.__name__ == 'InvalidPageError':
                    try:
                        fname = '/home/pse/PSE-engine/htmls/%s.html' % str(
                            gvar.task_id)
                        gvar.web_mgr.store_page_source(fname)
                        print_flushed("error html:", fname)
                    except:
                        print_flushed("Fail to dump html")
                        pass
                    err_msg = '================================ CRAWLING NOTIFICATION ============================== \n'
                    err_msg += 'There is invalid web page.\n Please check web page and xpath rule \n\nURL: {}}\n\n'.format(
                        str(gvar.task_url))
                    url = gvar.graph_mgr.get_slack_url()
                    post_notification_to_slack(err_msg, url)
                    err_msg = '================================ MESSAGE ============================== \n'
                    err_msg += 'There is invalid web page.\n Please check web page and xpath rule \n\nURL: {}}\n\n'.format(
                        str(gvar.task_url))
                    err_msg += '================================ Opeartor ==================================\n'
                    err_msg += 'BFSIterator \n\n'
                    err_msg += '================================ STACK TRACE ============================== \n' + \
                        str(traceback.format_exc())
                    gvar.graph_mgr.log_err_msg_of_task(gvar.task_id, err_msg)
                    raise
                elif e.__class__.__name__ == 'CheckXpathError':
                    try:
                        fname = '/home/pse/PSE-engine/htmls/%s.html' % str(
                            gvar.task_id)
                        gvar.web_mgr.store_page_source(fname)
                        print_flushed("error html:", fname)
                    except:
                        print_flushed("Fail to dump html")
                        pass
                    err_msg = '================================ CRAWLING NOTIFICATION ============================== \n'
                    err_msg += 'There is no element with input xpath rule for checking web page is loaded successfully.\nPlease check web page and xpath rule\n\nURL: {}\nXPath rule: {}\n\n'.format(
                        str(gvar.task_url), str(self.props['query']).replace("'", '"'))
                    url = gvar.graph_mgr.get_slack_url()
                    post_notification_to_slack(err_msg, url)
                    err_msg = '================================ MESSAGE ============================== \n'
                    err_msg += 'There is no element with input xpath rule for checking web page is loaded successfully.\nPlease check web page and xpath rule\n\nURL: {}\nXPath rule: {}\n\n'.format(
                        str(gvar.task_url), str(self.props['query']).replace("'", '"'))
                    err_msg += '================================ Opeartor ==================================\n'
                    err_msg += err_op_name + ' \n\n'
                    err_msg += '================================ STACK TRACE ============================== \n' + \
                        str(traceback.format_exc())
                    gvar.graph_mgr.log_err_msg_of_task(
                        gvar.task_id, err_msg)
                    raise


                err_cnt = err_cnt + 1
                if err_cnt >= 0:

                    if e.__class__.__name__ == 'WebMgrErr' or e.__class__.__name__ == 'TimeoutException':
                        try:
                            fname = '/home/pse/PSE-engine/htmls/%s.html' % str(
                                gvar.task_id)
                            gvar.web_mgr.store_page_source(fname)
                            print_flushed("error html:", fname)
                        except:
                            print_flushed("Fail to dump html")
                            pass
                        err_msg = '================================ CRAWLING NOTIFICATION ============================== \n'
                        err_msg += 'There is chromedriver error.\n\nURL: {}\n\n'.format(
                            str(gvar.task_url))
                        url = gvar.graph_mgr.get_slack_url()
                        post_notification_to_slack(err_msg, url)
                        err_msg = '================================ MESSAGE ============================== \n'
                        err_msg += 'There is chromedriver error.\n\nURL: {}\n\n'.format(
                            str(gvar.task_url))
                        err_msg += '================================ Opeartor ==================================\n'
                        err_msg += err_op_name + ' \n\n'
                        err_msg += '================================ STACK TRACE ============================== \n' + \
                            str(traceback.format_exc())
                        gvar.graph_mgr.log_err_msg_of_task(
                            gvar.task_id, err_msg)
                        gvar.profiling_info['web_error'] = True
                        raise
                    else:
                        try:
                            fname = '/home/pse/PSE-engine/htmls/%s.html' % str(
                                gvar.task_id)
                            gvar.web_mgr.store_page_source(fname)
                            print_flushed("error html:", fname)
                        except:
                            print_flushed("Fail to dump html")
                            pass
                        err_msg = '================================ CRAWLING NOTIFICATION ============================== \n'
                        err_msg += 'There is no element with input xpath rule of Key: {}.\nPlease check web page and xpath rule\n\nURL: {}\nKey: {}\nXPath rule: {}\n\n'.format(
                            str(e.key), str(gvar.task_url), str(e.key), str(e.xpath).replace("'", '"'))
                        url = gvar.graph_mgr.get_slack_url()
                        post_notification_to_slack(err_msg, url)
                        err_msg = '================================ MESSAGE ============================== \n'
                        err_msg += 'There is no element with input xpath rule of Key: {}.\nPlease check web page and xpath rule\n\nURL: {}\nKey: {}\nXPath rule: {}\n\n'.format(
                            str(e.key), str(gvar.task_url), str(e.key), str(e.xpath).replace("'", '"'))
                        err_msg += '================================ Opeartor ==================================\n'
                        err_msg += err_op_name + ' \n\n'
                        err_msg += '================================ STACK TRACE ============================== \n' + \
                            str(traceback.format_exc())
                        gvar.graph_mgr.log_err_msg_of_task(
                            gvar.task_id, err_msg)
                        raise OperatorError(e, self.props['id'])
                    # else:
                    #    fname = '/home/pse/PSE-engine/htmls/%s.html' % str(gvar.task_id)
                    #    gvar.web_mgr.store_page_source(fname)
                    #    print_flushed("error html:", fname)
                    #    err_msg = '================================== URL ==================================\n'
                    #    err_msg += ' ' + str(gvar.task_url) + '\n\n'
                    #    err_msg += '================================ Opeartor ==================================\n'
                    #    err_msg += err_op_name + ' \n\n'
                    #    err_msg += '================================ STACK TRACE ============================== \n' + \
                    #        str(traceback.format_exc())
                    #    gvar.graph_mgr.log_err_msg_of_task(gvar.task_id, err_msg)
                    #    raise OperatorError(e, self.props['id'])

                else:
                    gvar.web_mgr.restart(5)
                    print_flushed('err_cnt : ', err_cnt)


class OpenNode(BaseOperator):

    def run(self, gvar):
        try:
            op_start = time.time()
            op_id = self.props['id']
            label = self.props['label']
            parent_node_id = gvar.stack_nodes[-1]

            query = self.props['query']
            if 'indices' in self.props:
                query = self.set_query(
                    query, gvar.stack_indices, self.props['indices'])

            essential = self.props.get("essential", False)
            if type(essential) != type(True):
                essential = eval(essential)
            if essential:
                elements = gvar.web_mgr.get_elements_by_selenium_strong_(query)
            else:
                elements = gvar.web_mgr.get_elements_by_selenium_(query)

            num_elements = len(elements)
            print_flushed(num_elements, query)
            if num_elements == 0 and int(self.props.get('self', 0)) == 1:
                num_elements = 1

            for i in range(num_elements):
                print_flushed(
                    i, "-th loop#############################################")
                node_id = gvar.graph_mgr.create_node(
                    gvar.task_id, parent_node_id, label)
                gvar.stack_nodes.append(node_id)
                gvar.stack_indices.append(i)
                for op in self.operators:
                    op.run(gvar)
                gvar.stack_nodes.pop()
                gvar.stack_indices.pop()
            op_time = time.time() - op_start
            gvar.profiling_info[op_id] = {'op_time': op_time}
            return
        except Exception as e:
            if type(e) is OperatorError:
                raise e
            raise OperatorError(e, self.props['id'], self.props['query'])


class SendPhoneKeyOperator(BaseOperator):
    def run(self, gvar):
        try:
            op_id = self.props['id']
            op_start = time.time()
            print_flushed("Do SendPhoneKeys")

            number = input("varification number: ")
            query = self.props["query"]
            gvar.web_mgr.end_keys_to_elements_strong(query, number)
            time.sleep(int(column.get('delay', 0)))

            op_time = time.time() - op_start
            gvar.profiling_info[op_id] = {'op_time': op_time}
            return
        except Exception as e:
            raise OperatorError(e, self.props['id'], self.props['query'])
            return
        return


class WaitOperator(BaseOperator):
    def run(self, gvar):
        try:
            op_id = self.props['id']
            print_flushed("Do Wait {} secs".format(self.props.get('wait', 0)))
            time.sleep(int(self.props.get('wait', 0)))
            return
        except Exception as e:
            raise OperatorError(e, self.props['id'])
            return
        return


class ScrollOperator(BaseOperator):
    def run(self, gvar):
        try:
            op_id = self.props['id']
            print_flushed("Do Scroll")
            op_start = time.time()
            gvar.web_mgr.scroll_to_bottom()

            op_time = time.time() - op_start
            gvar.profiling_info[op_id] = {'op_time': op_time}
            return
        except Exception as e:
            if e.__class__.__name__ in selenium_chrome_erros:
                # if e.__class__.__name__ == 'WebDriverException' or e.__class__.__name__ == 'TimeoutException':
                print_flushed('Chrome Error in ScrollOperator')
                raise e
            else:
                fname = '/home/pse/PSE-engine/htmls/%s.html' % str(
                    gvar.task_id)
                raise OperatorError(e, self.props['id'])
        return


class HoverOperator(BaseOperator):
    def run(self, gvar):
        try:
            op_id = self.props['id']
            print_flushed("Do Hover")
            op_start = time.time()
            xpath = self.props['query']
            gvar.web_mgr.move_to_elements(xpath)

            op_time = time.time() - op_start
            gvar.profiling_info[op_id] = {'op_time': op_time}
            return
        except Exception as e:
            if e.__class__.__name__ in selenium_chrome_erros:
                # if e.__class__.__name__ == 'WebDriverException' or e.__class__.__name__ == 'TimeoutException':
                print_flushed('Chrome Error in HoverOperator')
                raise e
            else:
                fname = '/home/pse/PSE-engine/htmls/%s.html' % str(
                    gvar.task_id)
                raise OperatorError(e, self.props['id'], self.props['query'])

        return


class LoginOperator(BaseOperator):
    def run(self, gvar):
        try:
            op_id = self.props['id']
            op_start = time.time()
            print_flushed("before login")
            print_flushed(gvar.web_mgr.get_current_url())
            print_flushed("Do Login")
            gvar.web_mgr.login_by_xpath(self.props["user_id"], self.props["pwd"],
                                        self.props["user_id_query"], self.props["pwd_query"], self.props["click_query"])
            time.sleep(int(self.props.get('delay', 10)))
            op_time = time.time() - op_start
            print_flushed("after login")
            print_flushed(gvar.web_mgr.get_current_url())
            fname = '/home/pse/PSE-engine/htmls/test.html'
            gvar.web_mgr.store_page_source(fname)
            gvar.profiling_info[op_id] = {'op_time': op_time}
        except Exception as e:
            raise OperatorError(e, self.props['id'])


class SendKeysOperator(BaseOperator):
    def run(self, gvar):
        log_query = ''
        try:
            op_id = self.props['id']
            op_start = time.time()
            print_flushed("Do Input (SendKeys)")
            for column in self.props["queries"]:
                query = column["query"]
                log_query = query
                gvar.web_mgr.send_keys_to_elements(query, column['value'])
            op_time = time.time() - op_start
            gvar.profiling_info[op_id] = {'op_time': op_time}
        except Exception as e:
            raise OperatorError(e, self.props['id'], log_query)


class ClickOperator(BaseOperator):

    def run(self, gvar):
        log_query = ''
        try:
            time_sleep = int(self.props.get('delay', 0))
            op_id = self.props['id']
            op_start = time.time()
            print_flushed("Do Click")
            for column in self.props["queries"]:
                query = column["query"]
                log_query = query
                check_query = column.get("check_query", '').strip()
                if 'indices' in column:
                    query = self.set_query(
                        query, gvar.stack_indices, column['indices'])
                essential = column.get("essential", False)
                repeat = column.get("repeat", False)
                if type(essential) != type(True):
                    essential = eval(essential)
                if type(repeat) != type(True):
                    repeat = eval(repeat)
                if repeat:
                    gvar.web_mgr.click_elements_repeat(
                        query, check_query, time_sleep, gvar.task_url)
                else:
                    if essential:
                        gvar.web_mgr.click_elements_strong(query, check_query)
                    else:
                        gvar.web_mgr.click_elements(query, check_query)
                time.sleep(int(column.get('delay', 5)))
            op_time = time.time() - op_start
            gvar.profiling_info[op_id] = {'op_time': op_time}
            return
        except Exception as e:
            if e.__class__.__name__ in selenium_chrome_erros:
                # if e.__class__.__name__ == 'WebDriverException' or e.__class__.__name__ == 'TimeoutException' or e.__class__.__name__ ==  'StaleElementReferenceException':
                print_flushed('Chrome Error in ClickOperator')
                raise e
            else:
                fname = '/home/pse/PSE-engine/htmls/%s.html' % str(
                    gvar.task_id)
                raise OperatorError(e, self.props['id'], log_query)

        return


class MoveCursorOperator(BaseOperator):

    def run(self, gvar):
        log_query = ''
        try:
            op_id = self.props['id']
            op_start = time.time()
            print_flushed("Do MoveCursor")
            for column in self.props["queries"]:
                query = column["query"]
                log_query = query
                if 'indices' in column:
                    query = self.set_query(
                        query, gvar.stack_indices, column['indices'])
                essential = column.get("essential", False)
                if type(essential) != type(True):
                    essential = eval(essential)
                if essential:
                    gvar.web_mgr.move_to_elements_strong(query)
                else:
                    gvar.web_mgr.move_to_elements(query)
            op_time = time.time() - op_start
            gvar.profiling_info[op_id] = {'op_time': op_time}
        except Exception as e:
            if e.__class__.__name__ in selenium_chrome_erros:
                # if e.__class__.__name__ == 'WebDriverException' or e.__class__.__name__ == 'TimeoutException':
                print_flushed('Chrome Error in MoveCursorOperator')
                raise e
            else:
                fname = '/home/pse/PSE-engine/htmls/%s.html' % str(
                    gvar.task_id)
                raise OperatorError(e, self.props['id'], log_query)


class Expander(BaseOperator):

    def run_0(self, gvar):
        op_start = time.time()
        op_id = self.props['id']
        gvar.results[op_id] = [
            (gvar.task_id, gvar.stack_nodes[-1], [gvar.web_mgr.get_current_url()])]
        op_time = time.time() - op_start
        gvar.profiling_info[op_id] = {'op_time': op_time}

    def run_1(self, gvar):

        op_start = time.time()

        op_id = self.props['id']
        query = self.props['query']
        if 'indices' in self.props:
            query = self.set_query(
                query, gvar.stack_indices, self.props['indices'])
        attr = self.props["attr"]

        site = self.props.get("prefix", None)
        attr_delimiter = self.props.get("attr_delimiter", None)
        attr_idx = self.props.get("attr_idx", None)
        suffix = self.props.get("suffix", "")
        self_url = self.props.get('matchSelf', False)
        if type(self_url) != type(True):
            self_url = eval(self_url)
        no_matching_then_self = self.props.get('noMatchSelf', False)
        if type(no_matching_then_self) != type(True):
            no_matching_then_self = eval(no_matching_then_self)
        cur_url = gvar.web_mgr.get_current_url()

        xpaths_time = time.time()
        result = gvar.web_mgr.get_values_by_selenium(query, attr)
        #result = gvar.web_mgr.get_values_by_lxml(query, attr)
        xpaths_time = time.time() - xpaths_time

        # if url_query is not None:
        #  for idx, res in enumerate(result):
        #    result[idx] = int(result[idx])
        #  if len(result) == 0:
        #    if no_matching_then_self == 1: result = [gvar.web_mgr.get_current_url()]
        #  else:
        #    for idx, res in enumerate(result):
        #      result[idx] = cur_url.split('?')[0] + (url_query % int(result[idx]))
        # else:
        if attr_delimiter is not None:
            for idx, res in enumerate(result):
                result[idx] = result[idx].split(attr_delimiter)[
                    attr_idx] + str(suffix)
            if len(result) == 0:
                self_url = 1
                if no_matching_then_self == 1:
                    result = [gvar.web_mgr.get_current_url()]
            else:
                self_url = 0

        if site is not None:
            if len(result) == 0:
                if no_matching_then_self == 1:
                    result = [gvar.web_mgr.get_current_url()]
                # else:
                #  essential = self.props.get("essential", False)
                #  if type(essential) != type(True): essential = eval(essential)
                #  if essential: raise
            else:
                for idx, res in enumerate(result):
                    result[idx] = str(site) + str(res)
                if self_url == 1:
                    result.append(gvar.web_mgr.get_current_url())
        else:
            if len(result) == 0:
                if no_matching_then_self == 1:
                    result = [gvar.web_mgr.get_current_url()]
                # else:
                #  essential = self.props.get("essential", False)
                #  if type(essential) != type(True): essential = eval(essential)
                #  if essential: raise
            else:
                if self_url == 1:
                    result.append(gvar.web_mgr.get_current_url())
        if len(result) == 0:
            raise NoneDetailPageError(self.props['query'])
        gvar.results[op_id] = [(gvar.task_id, gvar.stack_nodes[-1], result)]
        op_time = time.time() - op_start
        gvar.profiling_info[op_id] = {
            'op_time': op_time,
            'xpaths_time': xpaths_time,
            'num_elements':  len(result)
        }
        return

    def run(self, gvar):
        try:
            if len(self.props.get("query", "").strip()) > 0:
                return self.run_1(gvar)
            else:
                return self.run_0(gvar)
        except Exception as e:
            if e.__class__.__name__ in selenium_chrome_erros:
                # if e.__class__.__name__ == 'WebDriverException' or e.__class__.__name__ == 'TimeoutException':
                print_flushed('Chrome Error in ExpanderOperator')
                raise e
            elif e.__class__.__name__ == 'NoneDetailPageError':
                raise e
            else:
                raise OperatorError(e, self.props['id'])


class ValuesScrapper(BaseOperator):

    def before(self, gvar):
        result = {}
        op_time = time.time()
        print_flushed('Do ValuesScrapper')
        op_id = self.props['id']
        pairs = self.props['queries']
        xpaths_time = ''
        build_time = ''
        log_query = ''
        log_key = ''
        try:

            build_time = time.time()
            gvar.web_mgr.build_lxml_tree()
            build_time = time.time() - build_time

            xpaths_time = time.time()
            for pair in pairs:
                key = pair['key']
                xpath = pair['query']
                log_query = xpath
                attr = pair['attr']
                print_flushed(pair)

                if xpath == '':
                    if attr == 'url':
                        result[key] = str(
                            gvar.web_mgr.get_current_url()).strip()
                else:
                    if 'indices' in pair:
                        print_flushed(xpath)
                        print_flushed(gvar.stack_indices)
                        print_flushed(pair['indices'])
                        xpath = self.set_query(
                            xpath, gvar.stack_indices, pair['indices'])
                    essential = pair.get('essential', False)
                    if type(essential) != type(True):
                        essential = eval(essential)
                    if attr == 'Default Value(constant)':
                        result[key] = xpath
                    else:
                        if attr == 'outerHTML':
                            if essential:
                                log_key = key
                                result[key] = gvar.web_mgr.get_subtree_with_style_strong(
                                    xpath)
                            else:
                                log_key = ''
                                result[key] = gvar.web_mgr.get_subtree_with_style(
                                    xpath)
                            continue
                        if attr == 'innerHTML':
                            if essential:
                                log_key = key
                                result[key] = gvar.web_mgr.get_subtree_no_parent_with_style_strong(
                                    xpath)
                            else:
                                log_key = ''
                                result[key] = gvar.web_mgr.get_subtree_no_parent_with_style(
                                    xpath)
                            continue
                        if essential:
                            log_key = key
                            result[key] = gvar.web_mgr.get_value_by_lxml_strong(
                                xpath, attr)
                        else:
                            log_key = ''
                            result[key] = gvar.web_mgr.get_value_by_lxml(
                                xpath, attr)
            xpaths_time = time.time() - xpaths_time
        except Exception as e:
            if e.__class__.__name__ in selenium_chrome_erros:
                # if e.__class__.__name__ == 'WebDriverException' or e.__class__.__name__ == 'TimeoutException':
                print_flushed('Chrome Error in ValuesScrapper')
                raise e
            else:
                raise OperatorError(e, self.props['id'], log_query, log_key)

        try:
            db_time = time.time()
            for key, value in result.items():
                gvar.graph_mgr.insert_node_property(
                    gvar.stack_nodes[-1], key, value)
            db_time = time.time() - db_time

            op_time = time.time() - op_time
            gvar.profiling_info[op_id] = {
                'op_time': op_time,
                'build_time': build_time,
                'xpaths_num': len(pairs),
                'xpaths_time': xpaths_time,
                'db_num': len(result),
                'db_time': db_time
            }
        except Exception as e:
            raise OperatorError(e, self.props['id'])
        return


class ListsScrapper(BaseOperator):

    def run(self, gvar):
        result = {}
        op_time = time.time()
        print_flushed('Do ListsScrapper')
        op_id = self.props['id']
        queries = self.props['queries']
        xpaths_time = ''
        build_time = ''
        log_query = ''
        log_key = ''
        try:

            build_time = time.time()
            gvar.web_mgr.build_lxml_tree()
            build_time = time.time() - build_time
            xpaths_time = time.time()

            for query in queries:
                key = query['key']
                xpath = query['query']
                log_query = xpath
                if 'indices' in query:
                    xpath = self.set_query(
                        xpath, gvar.stack_indices, query['indices'])
                attr = query['attr']
                essential = query.get('essential', False)
                if type(essential) != type(True):
                    essential = eval(essential)
                if essential:
                    log_key = key
                    result[key] = gvar.web_mgr.get_values_by_lxml_strong(
                        xpath, attr)
                else:
                    log_key = ''
                    result[key] = gvar.web_mgr.get_values_by_lxml(xpath, attr)

            xpaths_time = time.time() - xpaths_time
        except Exception as e:
            if e.__class__.__name__ in selenium_chrome_erros:
                # if e.__class__.__name__ == 'WebDriverException' or e.__class__.__name__ == 'TimeoutException':
                print_flushed('Chrome Error in ListsScrapper')
                raise e
            else:
                raise OperatorError(e, self.props['id'], log_query, log_key)
        try:
            db_time = time.time()
            for key, value in result.items():
                gvar.graph_mgr.insert_node_property(
                    gvar.stack_nodes[-1], key, value)
            db_time = time.time() - db_time

            op_time = time.time() - op_time
            gvar.profiling_info[op_id] = {
                'op_time': op_time,
                'build_time': build_time,
                'xpaths_time': xpaths_time,
                'db_time': db_time,
                'num_results': len(result)
            }
        except Exception as e:
            raise OperatorError(e, self.props['id'])
        return


class DictsScrapper(BaseOperator):

    def run(self, gvar):
        result = {}
        op_time = time.time()
        print_flushed('Do dictionary scrapper')
        op_id = self.props['id']
        queries = self.props['queries']
        xpaths_time = ''
        build_time = ''
        log_query = ''
        log_key = ''
        try:

            build_time = time.time()
            gvar.web_mgr.build_lxml_tree()
            build_time = time.time() - build_time

            result = {}

            xpaths_time = time.time()

            for query in queries:
                key = query['key']
                rows_query = query['rows_query']
                log_query = rows_query
                if 'rows_indices' in query:
                    rows_query = self.set_query(
                        rows_query, gvar.stack_indices, query['rows_indices'].strip())
                key_query = query['key_query']
                if 'key_indices' in query:
                    key_query = self.set_query(
                        key_query, gvar.stack_indices, query['key_indices'].strip())
                key_attr = query['key_attr']
                value_query = query['value_query']
                if 'value_indices' in query:
                    value_query = self.set_query(
                        value_query, gvar.stack_indices, query['value_indices'].strip())
                value_attr = query['value_attr']

                essential = query.get('essential', False)
                if type(essential) != type(True):
                    essential = eval(essential)

                if essential:
                    log_key = key
                    result[key] = gvar.web_mgr.get_key_values_by_lxml_strong(
                        rows_query, key_query, key_attr, value_query, value_attr)
                else:
                    log_key = ''
                    result[key] = gvar.web_mgr.get_key_values_by_lxml(
                        rows_query, key_query, key_attr, value_query, value_attr)
                title_query = query['title_query']
                result[key]['dictionary_title0'] = gvar.web_mgr.get_value_by_lxml(
                    title_query, 'alltext')

            xpaths_time = time.time() - xpaths_time
        except Exception as e:
            if e.__class__.__name__ in selenium_chrome_erros:
                # if e.__class__.__name__ == 'WebDriverException' or e.__class__.__name__ == 'TimeoutException':
                print_flushed('Chrome Error in DictionariesScrapper')
                raise e
            else:
                raise OperatorError(e, self.props['id'], log_query, log_key)

        try:
            db_time = time.time()
            for key, value in result.items():
                gvar.graph_mgr.insert_node_property(
                    gvar.stack_nodes[-1], key, value)
            db_time = time.time() - db_time

            op_time = time.time() - op_time
            gvar.profiling_info[op_id] = {
                'op_time': op_time,
                'build_time': build_time,
                'xpaths_time': xpaths_time,
                'db_time': db_time,
                'num_results': len(result)
            }
        except Exception as e:
            raise OperatorError(e, self.props['id'])
        return


class OptionListScrapper(BaseOperator):

    def run(self, gvar):
        op_start = time.time()
        print_flushed('Do OptionListScrapper')
        op_id = self.props['id']
        parent_node_id = gvar.stack_nodes[-1]
        xpaths_time = ''
        build_time = ''
        result = {}
        log_query = ''
        try:
            option_name_query = self.props['option_name_query']
            option_dropdown_query = self.props['option_dropdown_query']
            option_value_query = self.props['option_value_query']
            option_attr = self.props.get('option_attr', 'alltext')
            option_essential = self.props.get('option_essential', 'False')
            if option_attr == '':
                option_attr = 'alltext'
            log_query = option_name_query

            if type(option_essential) != type(True):
                option_essential = eval(option_essential)

            build_time = time.time()
            gvar.web_mgr.build_lxml_tree()
            build_time = time.time() - build_time

            xpaths_time = time.time()

            option_names = gvar.web_mgr.get_values_by_lxml(
                option_name_query, 'alltext')
            option_values = gvar.web_mgr.get_option_values_by_lxml(
                option_dropdown_query, option_value_query, option_attr, option_essential)

            for idx, option_name in enumerate(option_names):
                try:
                    result[option_name] = option_values[idx]
                except:
                    pass

            xpaths_time = time.time() - xpaths_time
        except Exception as e:
            if e.__class__.__name__ in selenium_chrome_erros:
                # if e.__class__.__name__ == 'WebDriverException' or e.__class__.__name__ == 'TimeoutException':
                print_flushed('Chrome Error in OptionListScrapper')
                raise e
            else:
                raise OperatorError(
                    e, self.props['id'], log_query, 'option list')

        try:
            db_time = time.time()
            # for key, value in result.items():
            print_flushed(result)
            gvar.graph_mgr.insert_node_property(
                gvar.stack_nodes[-1], 'option_list', result)
            db_time = time.time() - db_time

            op_time = time.time() - op_start
            gvar.profiling_info[op_id] = {
                'op_time': op_time,
                'build_time': build_time,
                'xpaths_time': xpaths_time,
                'db_time': db_time,
                'num_results': len(result)
            }
        except Exception as e:
            raise OperatorError(e, self.props['id'])
        return


class OptionMatrixScrapper(BaseOperator):

    def run(self, gvar):
        op_start = time.time()
        print_flushed('Do OptionMatrixScrapper')
        op_id = self.props['id']
        parent_node_id = gvar.stack_nodes[-1]
        xpaths_time = ''
        build_time = ''
        result = {}
        log_query = ''
        try:
            option_name_query = self.props['option_name_query']
            option_x_query = self.props['option_x_value_query']
            option_y_query = self.props['option_y_value_query']
            option_combination_value_query = self.props['option_matrix_row_wise_value_query']
            log_query = option_name_query

            build_time = time.time()
            gvar.web_mgr.build_lxml_tree()
            build_time = time.time() - build_time
            xpaths_time = time.time()

            option_names = gvar.web_mgr.get_values_by_lxml(
                option_name_query, 'alltext')
            option_x_value = gvar.web_mgr.get_values_by_lxml(
                option_x_query, 'alltext')
            option_y_value = gvar.web_mgr.get_values_by_lxml(
                option_y_query, 'alltext')
            option_combination_value = gvar.web_mgr.get_values_by_lxml(
                option_combination_value_query, 'alltext')

            for idx, option_name in enumerate(option_names):
                if idx == 0:
                    result[option_name] = option_x_value
                    result['option_matrix_col_name'] = [option_name]
                elif idx == 1:
                    result[option_name] = option_y_value
                    result['option_matrix_row_name'] = [option_name]

            if len(result) >= 1:
                result['option_maxtrix_value'] = option_combination_value

            xpaths_time = time.time() - xpaths_time

        except Exception as e:
            if e.__class__.__name__ in selenium_chrome_erros:
                # if e.__class__.__name__ == 'WebDriverException' or e.__class__.__name__ == 'TimeoutException':
                print_flushed('Chrome Error in OptionMatrixScrapper')
                raise e
            else:
                raise OperatorError(
                    e, self.props['id'], log_query, 'option matrix')

        try:
            db_time = time.time()

            print_flushed(result)
            gvar.graph_mgr.insert_node_property(
                gvar.stack_nodes[-1], 'option_matrix', result)
            db_time = time.time() - db_time

            op_time = time.time() - op_start
            result_len = 0
            if len(result) >= 1:
                result_len = len(result) - 1

            gvar.profiling_info[op_id] = {
                'op_time': op_time,
                'build_time': build_time,
                'xpaths_time': xpaths_time,
                'db_time': db_time,
                'num_results': result_len
            }
        except Exception as e:
            raise OperatorError(e, self.props['id'])
        return


worker_operators = {
    'BFSIterator': BFSIterator,
    'SendKeysOperator': SendKeysOperator,
    'LoginOperator': LoginOperator,
    'SendPhoneKeyOperator': SendPhoneKeyOperator,
    'ClickOperator': ClickOperator,
    'Expander': Expander,
    'ValuesScrapper': ValuesScrapper,
    'ListsScrapper': ListsScrapper,
    'DictsScrapper': DictsScrapper,
    'OpenNode': OpenNode,
    'OptionListScrapper': OptionListScrapper,
    'OptionMatrixScrapper': OptionMatrixScrapper,
    'OpenURL': BFSIterator,
    'Wait': WaitOperator,
    'Scroll': ScrollOperator,
    'Hover': HoverOperator,
    'Input': SendKeysOperator,
}


def materialize(lop, isRecursive):

    pop = worker_operators[lop["name"]]()
    pop.props = lop

    if isRecursive == False:
        pop.operators = lop['ops']
        return pop

    pop.operators = []
    for lchild in lop.get('ops', []):
        pchild = materialize(lchild, isRecursive)
        pop.operators.append(pchild)

    return pop


if __name__ == '__main__':
    gvar = GlovalVariable()

    gvar.graph_mgr = GraphManager()
    gvar.graph_mgr.connect(
        "host= port= user=pse password=pse dbname=pse")
    gvar.web_mgr = WebManager()
    gvar.task_id = 0
    gvar.exec_id = 0
    gvar.task_url = "https://outlet.arcteryx.com/us/en/shop/mens/zeta-sl-jacket-(us)"
    gvar.task_zipcode_url = "https://www.amazon.com/gp/delivery/ajax/address-change.html?locationType=LOCATION_INPUT&zipCode=94024&storeContext=offce-products&deviceType=web&pageType=detail&actionSource=glow"
    bfs_iterator = BFSIterator()
    bfs_iterator.props = {'id': 1, 'query': "//span[@id='productTitle']"}
    bfs_iterator.run(gvar)
