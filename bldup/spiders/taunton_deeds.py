from datetime import datetime
import re

import scrapy


class TauntonDeeds(scrapy.Spider):
    """tauntondeeds.com apartments spider"""

    name = "taunton_deeds"
    domain = "http://www.tauntondeeds.com/Searches/ImageSearch.aspx"
    "Page for parse"

    def start_requests(self) -> scrapy.Request:
        """
        First load of page (without parameters)
        :return: Content of page in scrapy.Request object
        :rtype: scrapy.Request
        """

        yield scrapy.Request(
            url="http://www.tauntondeeds.com/Searches/ImageSearch.aspx",
            callback=self.get_page
        )

    def get_page(self, response: scrapy.Request) -> scrapy.FormRequest:
        """
        Load the page with parameters for getting table size
        :param response: Object of page
        :type response: scrapy.Request
        :return: Content of page in scrapy.FormRequest object
        :rtype: scrapy.FormRequest
        """

        yield scrapy.FormRequest(
            url='http://www.tauntondeeds.com/Searches/ImageSearch.aspx',
            formdata={
                "ctl00$cphMainContent$txtLCEndDate$dateInput":
                    "2020-12-31-00-00-00",
                "ctl00$cphMainContent$txtLCSTartDate$dateInput":
                    "2020-01-01-00-00-00",
                "ctl00$cphMainContent$ddlLCDocumentType$vddlDropDown":
                    "101627",
                "ctl00$cphMainContent$btnSearchLC": "Search Land Court",
                '__VIEWSTATE': response.css(
                    'input#__VIEWSTATE::attr(value)'
                ).extract_first(),
            }, callback=self.get_tables)

    def get_tables(self, response: scrapy.FormRequest) -> scrapy.FormRequest:
        """
        Load all pages with parameters for getting apartment infos
        :param response: Object of page
        :type response: scrapy.FormRequest
        :return: Content of page in scrapy.FormRequest object
        :rtype: scrapy.FormRequest
        """

        # Get a pagination object
        pager = response.css("#ctl00_cphMainContent_gvSearchResults "
                             "tr.gridPager:first-child td table tr")

        # Load each page for parsing
        for page in range(1, len(pager.css("td")) + 1):
            yield scrapy.FormRequest(
                url='http://www.tauntondeeds.com/Searches/ImageSearch.aspx',
                formdata={
                    "ctl00_cphMainContent_txtLCSTartDate_dateInput_text":
                        "1/1/2020",
                    "ctl00_cphMainContent_txtLCEndDate_dateInput_text":
                        "12/31/2020",
                    "ctl00$cphMainContent$ddlLCDocumentType$vddlDropDown":
                        "101627",
                    '__VIEWSTATE': response.css(
                        'input#__VIEWSTATE::attr(value)'
                    ).extract_first(),
                    '__EVENTARGUMENT': f"Page${page}",
                    "__EVENTTARGET": "ctl00$cphMainContent$gvSearchResults",
                }, callback=self.get_rows)

    def get_rows(self, response: scrapy.FormRequest) -> dict:
        """
        Load each row in table and format it
        :param response: Object of page
        :type response: scrapy.FormRequest
        :return: Formatted dict with main information
        :rtype: dict
        """

        for table_row in response.css('#ctl00_cphMainContent_gvSearchResults '
                                      'tr.gridRow, #ctl00_cphMainContent_'
                                      'gvSearchResults tr.gridAltRow'):
            yield self.format_row_data(table_row)

    @staticmethod
    def format_row_data(row: scrapy.Selector) -> dict:
        """
        Format a table row to dict with main inforamtion
        :param row: HTML row object
        :type row: scrapy.Selector
        :return: Formatted data
        :rtype: dict
        """

        desc = row.css("td:nth-child(8) span::text").get()

        mask = re.compile(r"^(LOT [0-9A-Z]+)?|(LOTS [0-9 &]+)? ?(SP "
                          r"\d+-\w)?(.* [0-9-]+)[A-Z ,]+(\$(\d+\.00))?")

        groups = mask.split(desc)

        description = filter(len, map(
            lambda i: i.strip() if i is not None else "",
            (groups[1], groups[9], groups[10])
        ))

        book = row.css("td:nth-child(4)::text").get().strip()
        page_num = row.css("td:nth-child(5)::text").get().strip()

        return {
            "date": datetime.strptime(
                row.css("td:nth-child(2)::text").get(), "%m/%d/%Y"
            ),
            "type": row.css("td:nth-child(3)::text").get(),
            "book": book if book else None,
            "page_num": page_num if page_num else None,
            "doc_num": row.css("td:nth-child(6)::text").get(),
            "city": row.css("td:nth-child(7)::text").get(),
            "description": " ".join(description) if description else None,
            "cost": float(groups[13]) if groups[13] else None,
            "street_address": groups[11].strip() if groups[11] else None,
            "state": None,
            "zip": None,
        }
