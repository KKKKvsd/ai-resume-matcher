ALTER TABLE match_results
    ADD COLUMN matched_keywords TEXT NULL,
    ADD COLUMN missing_keywords TEXT NULL,
    ADD COLUMN evidence TEXT NULL,
    ADD COLUMN analysis_mode VARCHAR(30) NULL,
    ADD COLUMN error_message TEXT NULL;
