import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException

from app.api.search import search as search_endpoint
from app.services.aggregator import ResultAggregator
from app.services.searcher import SearchOrchestrator
from app.services.link_validator import LinkValidator
from app.sources import SearchResult
from app.sources.api_source import APISearchSource
from app.sources.sogou import SogouSearchSource
from app.sources.so360 import So360SearchSource
from app.sources.pansou import PanSouSearchSource


class SearchCoreTests(unittest.TestCase):
    def test_sogou_parser_accepts_spaces_inserted_into_urls(self):
        source = SogouSearchSource()
        html = """
        <div class='vrwrap'>
          电影资源 夸克链接: https:// pan.quark.cn / s / 52407cf256d7
        </div>
        """

        found = source._extract_cloud_urls_from_html(html, ["pan.quark.cn"])

        self.assertEqual(
            found,
            [{"url": "https://pan.quark.cn/s/52407cf256d7", "domain": "pan.quark.cn"}],
        )

    def test_sogou_title_removes_link_noise(self):
        source = SogouSearchSource()
        title = source._clean_title(
            "电影合集 链接：https:// pan.quark.cn/s/abc123"
        )

        self.assertEqual(title, "电影合集")

        nonstandard = source._clean_title(
            "惊喜电影：https:pan.quark.cn/s/abc123-惊喜电影：链接..."
        )
        self.assertEqual(nonstandard, "惊喜电影")

    def test_sogou_result_removes_summary_noise(self):
        source = SogouSearchSource()
        result = source._build_result(
            url="https://pan.quark.cn/s/abc123",
            title="...部限制电影合集》夸克链接：https://pan.quark.cn/s/abc123",
            full_text="...部限制电影合集》夸克 链接：https:// pan.quark.cn/s/abc123 公众号http://mp.weixin.qq.com/c... 2023-10-10 推荐您搜索",
        )

        self.assertEqual(result.title, "部限制电影合集》夸克")
        self.assertEqual(result.description, "")

    def test_aggregator_deduplicates_and_merges_metadata(self):
        first = SearchResult(
            title="资源",
            cloud_type="quark",
            cloud_name="夸克网盘",
            share_url="https://pan.quark.cn/s/abc",
            source_name="Bing",
        )
        second = SearchResult(
            title="资源",
            cloud_type="quark",
            cloud_name="夸克网盘",
            share_url="https://pan.quark.cn/s/abc",
            share_code="1234",
            description="高清资源",
            file_size="2GB",
            source_name="搜狗",
        )

        result = ResultAggregator.deduplicate([first, second])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].share_code, "1234")
        self.assertEqual(result[0].description, "高清资源")
        self.assertEqual(result[0].file_size, "2GB")

    def test_aggregator_relevance_prefers_complete_results(self):
        incomplete = SearchResult("A", "quark", "夸克网盘", "https://a")
        complete = SearchResult(
            "B", "quark", "夸克网盘", "https://b", share_code="1234", file_size="1GB"
        )

        result = ResultAggregator.sort([incomplete, complete], "relevance")

        self.assertEqual(result[0].share_url, "https://b")

    def test_aggregator_relevance_prefers_keyword_match(self):
        unrelated = SearchResult(
            "动漫壁纸", "quark", "夸克网盘", "https://unrelated", share_code="1234"
        )
        matched = SearchResult(
            "琅琊榜全集", "quark", "夸克网盘", "https://matched"
        )

        result = ResultAggregator.sort(
            [unrelated, matched], "relevance", keyword="琅琊榜"
        )

        self.assertEqual(result[0].share_url, "https://matched")

    def test_aggregator_filters_noise_when_relevant_results_exist(self):
        noisy = SearchResult("动漫壁纸", "quark", "夸克网盘", "https://noise")
        relevant = SearchResult("琅琊榜全集", "quark", "夸克网盘", "https://good")

        result = ResultAggregator.filter_by_keyword([noisy, relevant], "琅琊榜")

        self.assertEqual([item.share_url for item in result], ["https://good"])

    def test_aggregator_drops_results_without_keyword_match(self):
        noisy = SearchResult("动漫壁纸", "quark", "夸克网盘", "https://noise")

        result = ResultAggregator.filter_by_keyword([noisy], "琅琊榜")

        self.assertEqual(result, [])

    def test_aggregator_prefers_title_match_over_description_match(self):
        description_only = SearchResult(
            "资源站页面", "quark", "夸克网盘", "https://description",
            description="这里有琅琊榜资源"
        )
        title_match = SearchResult(
            "琅琊榜全集", "quark", "夸克网盘", "https://title"
        )

        result = ResultAggregator.filter_by_keyword(
            [description_only, title_match], "琅琊榜"
        )

        self.assertEqual([item.share_url for item in result], ["https://title"])

    def test_aggregator_matches_inserted_chinese_description_words(self):
        result = SearchResult(
            "资源分享页", "quark", "夸克网盘", "https://resource",
            description="电影资源分享"
        )

        self.assertEqual(
            ResultAggregator.filter_by_keyword([result], "电影分享"), [result]
        )

    def test_aggregator_requires_chinese_keyword_order(self):
        result = SearchResult(
            "分区里的电影和资料共享",
            "quark",
            "夸克网盘",
            "https://pan.quark.cn/s/resource",
        )

        self.assertEqual(
            ResultAggregator.filter_by_keyword([result], "电影分享"), []
        )

    def test_candidate_limit_keeps_multiple_cloud_types(self):
        results = [
            SearchResult(f"夸克{i}", "quark", "夸克网盘", f"https://q/{i}")
            for i in range(10)
        ] + [
            SearchResult(f"百度{i}", "baidu", "百度网盘", f"https://b/{i}")
            for i in range(3)
        ]

        limited = ResultAggregator.limit_diverse(results, 4)

        self.assertEqual(
            [item.cloud_type for item in limited],
            ["quark", "baidu", "quark", "baidu"],
        )

    def test_title_consistency_rejects_mismatched_resource(self):
        validator = LinkValidator()

        self.assertFalse(
            validator._titles_consistent(
                "来自搜索的电影分享资源", "植物大战僵尸安装程序"
            )
        )
        self.assertTrue(
            validator._titles_consistent(
                "琅琊榜 HD4K 全54集", "电视剧/琅琊榜 全54集"
            )
        )

    def test_aggregator_removes_empty_seo_titles(self):
        noisy = SearchResult(
            "《》-免费高清在线观看-电影时光",
            "quark",
            "夸克网盘",
            "https://noise",
            description="最新电影资源",
        )

        result = ResultAggregator.filter_by_keyword([noisy], "电影")

        self.assertEqual(result, [])

    def test_empty_pagination_has_zero_pages(self):
        result = ResultAggregator.paginate([], page=1, page_size=20)

        self.assertEqual(result["total"], 0)
        self.assertEqual(result["total_pages"], 0)

    def test_invalid_sort_is_rejected(self):
        async def run():
            with self.assertRaises(HTTPException) as context:
                await search_endpoint(
                    kw="测试",
                    types=None,
                    page=1,
                    size=20,
                    sort="invalid",
                    refresh=False,
                    db=None,
                )
            self.assertEqual(context.exception.status_code, 400)

        asyncio.run(run())

    def test_source_config_is_loaded(self):
        sources = SearchOrchestrator().get_sources()
        names = {source["name"] for source in sources}

        self.assertIn("必应搜索", names)
        self.assertIn("搜狗搜索", names)
        self.assertIn("百度搜索", names)
        self.assertFalse(next(s["enabled"] for s in sources if s["name"] == "百度搜索"))
        self.assertIn("PanSou聚合", names)
        self.assertTrue(next(s["enabled"] for s in sources if s["name"] == "PanSou聚合"))
        self.assertFalse(next(s["enabled"] for s in sources if s["name"] == "360搜索"))

    def test_360_parser_extracts_share_url(self):
        source = So360SearchSource()
        found = source._extract_urls(
            "电影资源 https://pan.quark.cn/s/abc123", ["pan.quark.cn"]
        )

        self.assertEqual(found, [("https://pan.quark.cn/s/abc123", "pan.quark.cn")])

    def test_api_source_nested_mapping(self):
        source = APISearchSource("测试", "https://example.invalid")
        result = source._map_result(
            {
                "title": "测试资源",
                "cloud_type": "quark",
                "share_url": "https://pan.quark.cn/s/test",
                "password": "abcd",
            }
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.cloud_name, "夸克网盘")
        self.assertEqual(result.share_url, "https://pan.quark.cn/s/test")

    def test_pansou_keeps_each_link_own_title(self):
        source = PanSouSearchSource()
        results = source._parse_payload(
            {
                "data": {
                    "merged_by_type": {
                        "quark": [
                            {
                                "url": "https://pan.quark.cn/s/first123",
                                "note": "电影甲 4K",
                                "source": "tg:channel-a",
                            },
                            {
                                "url": "https://pan.quark.cn/s/second456",
                                "note": "电影乙 1080P",
                                "source": "tg:channel-b",
                            },
                        ]
                    }
                }
            }
        )

        self.assertEqual(
            [(item.share_url, item.title) for item in results],
            [
                ("https://pan.quark.cn/s/first123", "电影甲 4K"),
                ("https://pan.quark.cn/s/second456", "电影乙 1080P"),
            ],
        )

    def test_pansou_rejects_url_with_wrong_cloud_type(self):
        source = PanSouSearchSource()
        results = source._parse_payload(
            {
                "data": {
                    "merged_by_type": {
                        "quark": [
                            {
                                "url": "https://pan.baidu.com/s/not-quark",
                                "note": "错误归类",
                            }
                        ]
                    }
                }
            }
        )

        self.assertEqual(results, [])

    def test_pansou_filters_requested_cloud_type(self):
        source = PanSouSearchSource()
        results = source._parse_payload(
            {
                "data": {
                    "merged_by_type": {
                        "quark": [{
                            "url": "https://pan.quark.cn/s/quark123",
                            "note": "夸克资源",
                        }],
                        "baidu": [{
                            "url": "https://pan.baidu.com/s/baidu123",
                            "note": "百度资源",
                        }],
                    }
                }
            },
            ["quark"],
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].cloud_type, "quark")

    def test_pansou_falls_back_to_local_filter_when_filtered_request_fails(self):
        async def run():
            source = PanSouSearchSource()
            payload = {
                "data": {
                    "merged_by_type": {
                        "quark": [{
                            "url": "https://pan.quark.cn/s/fallback123",
                            "note": "回退夸克资源",
                        }],
                        "baidu": [{
                            "url": "https://pan.baidu.com/s/fallback456",
                            "note": "不应出现的百度资源",
                        }],
                    }
                }
            }
            with patch.object(
                source,
                "_request_payload",
                new=AsyncMock(side_effect=[None, payload]),
            ):
                return await source.search("测试", ["quark"])

        results = asyncio.run(run())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].cloud_type, "quark")


class AsyncSmokeTests(unittest.TestCase):
    def test_sogou_parser_can_be_called_from_async_context(self):
        async def run():
            source = SogouSearchSource()
            return source._extract_cloud_urls_from_html(
                "https:// pan.quark.cn/s/abc123", ["pan.quark.cn"]
            )

        self.assertEqual(asyncio.run(run())[0]["url"], "https://pan.quark.cn/s/abc123")

    def test_quark_validator_accepts_confirmed_resource(self):
        async def run():
            def handler(request: httpx.Request) -> httpx.Response:
                return httpx.Response(
                    200,
                    json={
                        "status": 200,
                        "code": 0,
                        "message": "ok",
                        "data": {"title": "琅琊榜全集", "file_num": 1},
                    },
                    request=request,
                )

            validator = LinkValidator()
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(handler)
            ) as client:
                return await validator._check_quark(
                    client,
                    SearchResult(
                        "琅琊榜全集",
                        "quark",
                        "夸克网盘",
                        "https://pan.quark.cn/s/valid123",
                    ),
                )

        result = asyncio.run(run())
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.verified_title, "琅琊榜全集")

    def test_quark_validator_rejects_expired_resource(self):
        async def run():
            def handler(request: httpx.Request) -> httpx.Response:
                return httpx.Response(
                    404,
                    json={"status": 404, "code": 41011, "message": "分享地址已失效"},
                    request=request,
                )

            validator = LinkValidator()
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(handler)
            ) as client:
                return await validator._check_quark(
                    client,
                    SearchResult(
                        "过期资源",
                        "quark",
                        "夸克网盘",
                        "https://pan.quark.cn/s/expired123",
                    ),
                )

        result = asyncio.run(run())
        self.assertEqual(result.status, "invalid")


if __name__ == "__main__":
    unittest.main()
