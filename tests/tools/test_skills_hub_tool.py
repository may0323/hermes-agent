"""Tests for tools/skills_hub_tool.py — Skills management tools."""

import json

import pytest

from tools.skills_hub_tool import (
    SKILLS_CATEGORIES,
    check_skill_compatibility_tool,
    get_skill_details_tool,
    list_skills_tool,
    search_skills_tool,
)


class TestListSkillsTool:
    def test_list_all_skills(self):
        result = list_skills_tool()
        data = json.loads(result)
        assert data["success"] is True
        assert "skills" in data["data"]
        assert "categories" in data["data"]
        assert len(data["data"]["categories"]) == 5
        assert data["data"]["total_count"] > 0

    def test_list_skills_by_category_coding(self):
        result = list_skills_tool(category="coding")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["category"] == "coding"
        assert len(data["data"]["skills"]) == 4

    def test_list_skills_by_category_research(self):
        result = list_skills_tool(category="research")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["category"] == "research"
        assert len(data["data"]["skills"]) == 4

    def test_list_skills_by_category_creative(self):
        result = list_skills_tool(category="creative")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["category"] == "creative"

    def test_list_skills_by_category_automation(self):
        result = list_skills_tool(category="automation")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["category"] == "automation"

    def test_list_skills_by_category_communication(self):
        result = list_skills_tool(category="communication")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["category"] == "communication"

    def test_list_skills_invalid_category(self):
        result = list_skills_tool(category="invalid_category")
        data = json.loads(result)
        assert data["success"] is False
        assert data["error_code"] == "INVALID_CATEGORY"

    def test_list_skills_case_insensitive(self):
        result = list_skills_tool(category="CODING")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["category"] == "coding"


class TestSearchSkillsTool:
    def test_search_by_code_keyword(self):
        result = search_skills_tool(query="code")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["query"] == "code"
        assert len(data["data"]["matches"]) > 0

    def test_search_by_analyze_keyword(self):
        result = search_skills_tool(query="analyze")
        data = json.loads(result)
        assert data["success"] is True
        assert len(data["data"]["matches"]) > 0

    def test_search_by_debugging_keyword(self):
        result = search_skills_tool(query="debugging")
        data = json.loads(result)
        assert data["success"] is True
        matches = data["data"]["matches"]
        skill_names = [m["name"] for m in matches]
        assert "debugging" in skill_names

    def test_search_by_write_keyword(self):
        result = search_skills_tool(query="write")
        data = json.loads(result)
        assert data["success"] is True
        matches = data["data"]["matches"]
        skill_names = [m["name"] for m in matches]
        assert "writing" in skill_names

    def test_search_returns_relevance_scores(self):
        result = search_skills_tool(query="code")
        data = json.loads(result)
        matches = data["data"]["matches"]
        for match in matches:
            assert "score" in match
            assert "description" in match

    def test_search_empty_query_rejected(self):
        result = search_skills_tool(query="")
        data = json.loads(result)
        assert data["success"] is False
        assert data["error_code"] == "EMPTY_QUERY"

    def test_search_whitespace_query_rejected(self):
        result = search_skills_tool(query="   ")
        data = json.loads(result)
        assert data["success"] is False
        assert data["error_code"] == "EMPTY_QUERY"

    def test_search_no_matches(self):
        result = search_skills_tool(query="xyznonexistent")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["total_matches"] == 0

    def test_search_max_10_results(self):
        result = search_skills_tool(query="a e i o u")
        data = json.loads(result)
        assert data["success"] is True
        assert len(data["data"]["matches"]) <= 10

    def test_search_multiple_words(self):
        result = search_skills_tool(query="code analyze")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["query"] == "code analyze"


class TestGetSkillDetailsTool:
    def test_get_details_for_code_analysis(self):
        result = get_skill_details_tool(skill_name="code_analysis")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["name"] == "code_analysis"
        assert data["data"]["category"] == "coding"
        assert "description" in data["data"]
        assert "capabilities" in data["data"]
        assert "use_cases" in data["data"]

    def test_get_details_for_debugging(self):
        result = get_skill_details_tool(skill_name="debugging")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["name"] == "debugging"
        assert "error diagnosis" in " ".join(data["data"]["capabilities"]).lower()

    def test_get_details_for_web_search(self):
        result = get_skill_details_tool(skill_name="web_search")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["category"] == "research"

    def test_get_details_with_space_replaced(self):
        result = get_skill_details_tool(skill_name="code generation")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["name"] == "code_generation"

    def test_get_details_case_insensitive(self):
        result = get_skill_details_tool(skill_name="CODE_REVIEW")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["name"] == "code_review"

    def test_get_details_skill_not_found(self):
        result = get_skill_details_tool(skill_name="nonexistent_skill")
        data = json.loads(result)
        assert data["success"] is False
        assert data["error_code"] == "SKILL_NOT_FOUND"

    def test_get_details_empty_skill_name_rejected(self):
        result = get_skill_details_tool(skill_name="")
        data = json.loads(result)
        assert data["success"] is False
        assert data["error_code"] == "EMPTY_SKILL_NAME"

    def test_get_details_known_skill(self):
        result = get_skill_details_tool(skill_name="data_analysis")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["category"] == "research"


class TestCheckSkillCompatibilityTool:
    def test_code_analysis_with_code_context(self):
        result = check_skill_compatibility_tool(
            skill_name="code_analysis",
            context="I need to analyze this Python code for patterns and syntax errors"
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["skill_name"] == "code_analysis"
        assert data["data"]["compatibility_score"] > 0.3

    def test_debugging_with_error_context(self):
        result = check_skill_compatibility_tool(
            skill_name="debugging",
            context="My application is crashing with an error exception"
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["skill_name"] == "debugging"
        assert data["data"]["keywords_matched"] > 0

    def test_web_search_with_search_context(self):
        result = check_skill_compatibility_tool(
            skill_name="web_search",
            context="I need to search the web for information"
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["compatibility_score"] > 0.4

    def test_documentation_with_doc_context(self):
        result = check_skill_compatibility_tool(
            skill_name="documentation",
            context="I need to write documentation for my API and create a guide"
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["compatibility_score"] >= 0.4

    def test_no_matching_keywords(self):
        result = check_skill_compatibility_tool(
            skill_name="code_analysis",
            context="just some random text with no relevant keywords"
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["context_relevance"] is False

    def test_empty_skill_name_rejected(self):
        result = check_skill_compatibility_tool(
            skill_name="",
            context="some context"
        )
        data = json.loads(result)
        assert data["success"] is False
        assert data["error_code"] == "EMPTY_SKILL_NAME"

    def test_empty_context_rejected(self):
        result = check_skill_compatibility_tool(
            skill_name="code_analysis",
            context=""
        )
        data = json.loads(result)
        assert data["success"] is False
        assert data["error_code"] == "EMPTY_CONTEXT"

    def test_recommendation_levels(self):
        result = check_skill_compatibility_tool(
            skill_name="scheduling",
            context="I need to schedule a cron job for periodic tasks"
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["recommendation"] in (
            "highly_recommended",
            "recommended",
            "may_work",
            "not_recommended",
            "neutral"
        )

    def test_skill_name_with_space_normalized(self):
        result = check_skill_compatibility_tool(
            skill_name="code review",
            context="review my code for bugs"
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["skill_name"] == "code_review"


class TestSkillsCategories:
    def test_all_categories_have_skills(self):
        for category, skills in SKILLS_CATEGORIES.items():
            assert len(skills) > 0

    def test_categories_match_schema(self):
        expected = {"coding", "research", "creative", "automation", "communication"}
        assert set(SKILLS_CATEGORIES.keys()) == expected

    def test_skills_can_appear_in_multiple_categories(self):
        documentation_count = sum(1 for skills in SKILLS_CATEGORIES.values() if "documentation" in skills)
        assert documentation_count >= 1
