-- ==========================================================================
-- SANITIZED EXAMPLE: study-posting audit report source query
--
-- This file is documentation and a starting template. It is not expected to
-- run unchanged.
--
-- To use it:
--
--   1. Copy this file to input/audit-rows.sql.
--   2. Replace YOUR_HR_DATABASE_LINK with the locally configured Oracle
--      database-link name.
--   3. Replace EXCLUDED_CAMPUS_ID_1 and EXCLUDED_CAMPUS_ID_2 with locally
--      approved test, service, or system-account identifiers. Add or remove
--      entries as required by the operational reporting policy.
--   4. Review all table, view, and database-link names for the target
--      environment.
--   5. Confirm that the query returns no more than one row per ID.
--   6. Keep the final projected column names synchronized with
--      input/audit-schema.json.
--
-- The report preserves every returned row in records.csv. It selects rows for
-- analysis when:
--
--   ATTEMPT_TYPE = 'AI'
--   ATTEMPT_RESULT = 'COMPLETE'
--
-- A selected row must also have END_TIME and all three analysis payloads.
-- Missing required values on a selected row are treated as inconsistent source
-- data and cause the current fail-fast report run to fail.
--
-- Manual and incomplete attempts remain in records.csv without field metrics.
--
-- STACK_TRACE is intentionally not projected. If STACK_TRACE is present in
-- the source query, its projection is removed from this sanitized example.
-- Stack-trace content is excluded from report output.
--
-- SQL bind values, if added later, must be passed separately through the
-- database driver. Never interpolate configuration values into SQL text.
-- ==========================================================================

WITH
 dept_current AS (
     SELECT /*+ MATERIALIZE */ deptid, dept_descr, dept_grp_campus_descr
     FROM (
         SELECT d.deptid, d.dept_descr, d.dept_grp_campus_descr,
                ROW_NUMBER() OVER (PARTITION BY d.deptid ORDER BY d.dept_effdt DESC) AS rn
         FROM hr_department@YOUR_HR_DATABASE_LINK d
         WHERE d.dept_eff_status = 'A'
     )
     WHERE rn = 1
 ),
 jobcode_current AS (
     SELECT /*+ MATERIALIZE */ jobcode, jobcode_descr
     FROM (
         SELECT jc.jobcode, jc.jobcode_descr,
                ROW_NUMBER() OVER (PARTITION BY jc.jobcode ORDER BY jc.jobcode_effdt DESC) AS rn
         FROM hr_jobcode@YOUR_HR_DATABASE_LINK jc
         WHERE jc.jobcode_eff_status = 'A'
     )
     WHERE rn = 1
 ),
 job_events AS (
     SELECT /*+ MATERIALIZE */
         lower(hpd.campus_id)||'@umich.edu' AS email,
         j.emplid, j.empl_rcd, j.job_effdt, j.job_effseq,
         j.job_action, j.job_action_descr,
         j.empl_status, j.reg_temp, j.fte, j.appt_deptid, j.jobcode,
         j.job_indicator,
         j.appt_dept_grp_descr       AS appt_dept_grp_descr,
         dc.dept_descr               AS current_dept_descr,
         dc.dept_grp_campus_descr    AS current_campus_descr,
         jcc.jobcode_descr           AS current_jobcode_descr,
         LAG(j.jobcode)     OVER (PARTITION BY j.emplid, j.empl_rcd ORDER BY j.job_effdt, j.job_effseq) AS prev_jobcode,
         LAG(j.appt_deptid) OVER (PARTITION BY j.emplid, j.empl_rcd ORDER BY j.job_effdt, j.job_effseq) AS prev_deptid,
         LAG(j.reg_temp)    OVER (PARTITION BY j.emplid, j.empl_rcd ORDER BY j.job_effdt, j.job_effseq) AS prev_reg_temp
     FROM hr_job@YOUR_HR_DATABASE_LINK j
     JOIN hr_personal_data@YOUR_HR_DATABASE_LINK hpd
       ON j.emplid = hpd.emplid
     LEFT JOIN dept_current dc     ON dc.deptid   = j.appt_deptid
     LEFT JOIN jobcode_current jcc ON jcc.jobcode = j.jobcode
     -- Replace these placeholders with locally approved test, service, or
     -- system accounts that must be excluded from operational reporting.
     -- Add or remove entries according to the applicable reporting policy.
     WHERE hpd.campus_id NOT IN (
         'EXCLUDED_CAMPUS_ID_1',
         'EXCLUDED_CAMPUS_ID_2'
     )
     -- OPTIONAL performance filter across the DB link — restrict to campus_ids
     -- that actually appear as study posting authors or PIs. Uncomment to use:
      AND lower(hpd.campus_id)||'@umich.edu' IN (
            SELECT DISTINCT REPLACE(spa.user_name,'shib:','')
              FROM study_posting_audit spa
            UNION
            SELECT DISTINCT vestm.imported_team_member_user_name
              FROM v_eres_study_team_member vestm
             WHERE vestm.role = 'PI'
         )
 ),
 flagged AS (
     SELECT e.*,
            CASE
              WHEN prev_jobcode IS NULL
                OR jobcode      <> prev_jobcode
                OR appt_deptid  <> prev_deptid
                OR NVL(reg_temp,'~') <> NVL(prev_reg_temp,'~')
              THEN 1 ELSE 0
            END AS seg_start
     FROM job_events e
 ),
 grp AS (
     SELECT f.*,
            SUM(seg_start) OVER (PARTITION BY emplid, empl_rcd
                                 ORDER BY job_effdt, job_effseq
                                 ROWS UNBOUNDED PRECEDING) AS seg_id
     FROM flagged f
 ),
 segments AS (
     SELECT
         emplid, email, empl_rcd, seg_id,
         MIN(job_effdt) AS segment_start_dt,
         LEAD(MIN(job_effdt)) OVER (PARTITION BY emplid, empl_rcd ORDER BY seg_id) AS next_seg_start,
         MAX(CASE WHEN job_action IN ('TER','RET','RWP','TWP') THEN job_effdt END) AS term_action_dt,
         MAX(CASE WHEN empl_status IN ('A','W','L','P')        THEN job_effdt END) AS last_active_dt,
         MAX(appt_deptid)           KEEP (DENSE_RANK LAST  ORDER BY job_effdt, job_effseq) AS appt_deptid,
         MAX(current_dept_descr)    KEEP (DENSE_RANK LAST  ORDER BY job_effdt, job_effseq) AS dept_descr,
         MAX(appt_dept_grp_descr)   KEEP (DENSE_RANK LAST  ORDER BY job_effdt, job_effseq) AS school,
         MAX(current_campus_descr)  KEEP (DENSE_RANK LAST  ORDER BY job_effdt, job_effseq) AS campus_descr,
         MAX(jobcode)               KEEP (DENSE_RANK LAST  ORDER BY job_effdt, job_effseq) AS jobcode,
         MAX(current_jobcode_descr) KEEP (DENSE_RANK LAST  ORDER BY job_effdt, job_effseq) AS jobcode_descr,
         MAX(reg_temp)              KEEP (DENSE_RANK LAST  ORDER BY job_effdt, job_effseq) AS reg_temp,
         MAX(fte)                   KEEP (DENSE_RANK LAST  ORDER BY job_effdt, job_effseq) AS fte,
         MAX(job_indicator)         KEEP (DENSE_RANK LAST  ORDER BY job_effdt, job_effseq) AS job_indicator,
         MIN(job_action_descr)      KEEP (DENSE_RANK FIRST ORDER BY job_effdt, job_effseq) AS entry_action
     FROM grp
     GROUP BY emplid, email, empl_rcd, seg_id
 ),
 hr_jobs AS (
     SELECT
         s.emplid,
         s.email,
         s.empl_rcd,
         s.segment_start_dt AS job_effective_date,
         NVL(
           CASE
             -- Termination wins: last day held = day before termination effdt
             WHEN s.term_action_dt IS NOT NULL
              AND (s.last_active_dt IS NULL OR s.term_action_dt >= s.last_active_dt)
                  THEN s.term_action_dt - 1
             -- Otherwise a continuous next segment follows
             WHEN s.next_seg_start IS NOT NULL
                  THEN s.next_seg_start - 1
             ELSE NULL
           END,
           DATE '9999-12-31'   -- open/current segment -> effectively "still active"
         ) AS job_end_date,
         s.jobcode,
         s.jobcode_descr AS title,
         DECODE(s.appt_deptid, '0', 'N/A', NULL, 'N/A', s.dept_descr) AS department,
         s.school AS school,
         DECODE(TRIM(s.job_indicator), 'P', 1, 0) AS primary_appointment
     FROM segments s
     -- Keep only valid segments (mirrors the authoritative WHERE clause)
     WHERE NVL(
             CASE
               WHEN s.term_action_dt IS NOT NULL
                AND (s.last_active_dt IS NULL OR s.term_action_dt >= s.last_active_dt)
                    THEN s.term_action_dt - 1
               WHEN s.next_seg_start IS NOT NULL
                    THEN s.next_seg_start - 1
               ELSE NULL
             END,
             DATE '9999-12-31'
           ) >= s.segment_start_dt
 ),
 attempt_author_appointments AS (
     SELECT spa.id AS study_posting_audit_id,
     RTRIM(
         XMLCAST(
             XMLAGG(
                 XMLELEMENT(e,
                     hj.title||':'||hj.department||':'||hj.school||', '
                 )
                 ORDER BY hj.primary_appointment DESC, hj.title
             ) AS CLOB
         ),
         ', '
     ) AS current_appointments
     FROM study_posting_audit spa
     JOIN hr_jobs hj
       ON 'shib:' || hj.email = spa.user_name
      AND spa.start_time BETWEEN hj.job_effective_date AND hj.job_end_date
     GROUP BY spa.id
 ),
 attempt_pi_appointments AS (
     SELECT spa.id AS study_posting_audit_id,
     RTRIM(
         XMLCAST(
             XMLAGG(
                 XMLELEMENT(e,
                     hj.title||':'||hj.department||':'||hj.school||', '
                 )
                 ORDER BY hj.primary_appointment DESC, hj.title
             ) AS CLOB
         ),
         ', '
     ) AS current_appointments
     FROM study_posting_audit spa
     JOIN v_eres_study_team_member vestm
       ON vestm.imported_study_id = spa.study_num
      AND vestm.role = 'PI'
     JOIN hr_jobs hj
       ON hj.email = vestm.imported_team_member_user_name
      AND spa.start_time BETWEEN hj.job_effective_date AND hj.job_end_date
     GROUP BY spa.id
 ),
 all_logins AS (
     SELECT la.user_id, la.user_name, la.successful_login_time login_time
       FROM login_audit la, study_posting_audit spa
      WHERE spa.user_name = la.user_name
     UNION ALL
     SELECT la.user_id, la.user_name, la.successful_login_time
       FROM yhr_umich_backup.login_audit la, study_posting_audit spa
      WHERE spa.user_name = la.user_name
 ),
 user_login_days AS (
     SELECT
         user_name,
         MIN(login_time) min_login_time,
         MAX(login_time) max_login_time,
         COUNT(DISTINCT TRUNC(login_time)) AS login_days
     FROM all_logins
     GROUP BY user_name
 ),
 study_stats AS (
     SELECT s.id,
            s.study_num,
            s.publishable,
            s.created_by_id,
            s.created_date,
            d.department,
            pt.participant_type
     FROM study s
     LEFT JOIN (
         SELECT spv.study_id,
                lv.display_text AS department
         FROM study_property_value spv
         JOIN entity_property ep
           ON ep.id = spv.entity_property_id
          AND ep.name = 'department'
         JOIN study_prop_val_lookup_val spvlv
           ON spv.id = spvlv.property_value_id
         JOIN lookup_value lv
           ON lv.id = spvlv.lookup_value_id
     ) d
       ON d.study_id = s.id
     LEFT JOIN (
         SELECT spv.study_id,
                CASE
                  WHEN MAX(CASE WHEN lv.name = 'HEALTHY'   THEN 1 ELSE 0 END) = 1
                   AND MAX(CASE WHEN lv.name = 'CONDITION' THEN 1 ELSE 0 END) = 1
                       THEN 'Both'
                  WHEN MAX(CASE WHEN lv.name = 'HEALTHY'   THEN 1 ELSE 0 END) = 1
                       THEN 'HEALTHY'
                  WHEN MAX(CASE WHEN lv.name = 'CONDITION' THEN 1 ELSE 0 END) = 1
                       THEN 'CONDITION'
                END AS participant_type
         FROM study_property_value spv
         JOIN entity_property ep
           ON ep.id = spv.entity_property_id
          AND ep.name = 'participantType'
         JOIN study_prop_val_lookup_val spvlv
           ON spv.id = spvlv.property_value_id
         JOIN lookup_value lv
           ON lv.id = spvlv.lookup_value_id
         GROUP BY spv.study_id
     ) pt
       ON pt.study_id = s.id
 ),
 stm_roles AS (
     SELECT au.id user_id, au.user_name, au.email, au.first_name, au.last_name, au.middle_name,
            stm.study_id, s.study_num, stm.role stm_role, vestm.role eresearch_role
       FROM app_user au
       LEFT JOIN study_team_member stm ON au.id = stm.user_id
       LEFT JOIN study s               ON s.id  = stm.study_id
       LEFT JOIN v_eres_study_team_member vestm
              ON 'shib:'||vestm.imported_team_member_user_name = au.user_name
             AND s.study_num = vestm.imported_study_id
      WHERE INSTR(au.user_name, 'shib:') > 0
 ),
 study_counts AS (
     SELECT spa.id study_posting_audit_id,
            spa.user_name,
            spa.study_num,
            spa.start_time,
            spa.end_time,
            /* Number of studies previously created by this user (as-of attempt) */
            (
              SELECT COUNT(*)
              FROM study s
              WHERE s.created_by_id = au.id
                AND s.created_date  < spa.end_time
                AND s.study_num    <> spa.study_num
            ) AS prior_created_count,
            /* Total studies ever created by this user */
            (
              SELECT COUNT(*)
              FROM study s
              WHERE s.created_by_id = au.id
            ) AS total_created_count,
            /* Other studies this user belongs to, excluding the study being attempted */
            (
              SELECT COUNT(*)
              FROM study_team_member stm
              JOIN study s ON s.id = stm.study_id
              WHERE stm.user_id  = au.id
                AND s.study_num <> spa.study_num
            ) AS member_of_other_studies_count
     FROM study_posting_audit spa
     JOIN app_user au
       ON au.user_name = spa.user_name
 )
 SELECT spa.id, TO_CHAR(spa.start_time, 'MM/DD/YYYY HH24:MI:SS.FF6') start_time, TO_CHAR(spa.end_time, 'MM/DD/YYYY HH24:MI:SS.FF6') end_time,
        DECODE(spga.source_type, NULL, 'MANUAL', 'AI') attempt_type,
        CASE
          WHEN spgae.stack_trace IS NOT NULL
               THEN 'AI_ERROR'
          WHEN spga.latency_ms = 0 AND spgae.stack_trace IS NULL
               THEN 'AI_ERROR_WITHOUT_STACK_TRACE'
          WHEN spa.end_time IS NULL
               THEN 'USER_DROPPED'
          ELSE 'COMPLETE'
        END attempt_result,
        DECODE(sr.user_id, NULL, 'EXISTED', 'NON_EXISTENT') USER_TYPE,
        spa.study_num, TO_CHAR(ss.created_date, 'MM/DD/YYYY HH24:MI:SS.FF6') created_date, ss.created_by_id, ss.publishable,
        ss.department study_department, ss.participant_type study_participant_type,
        sr.user_id, spa.user_name author_user_name,
        sr.stm_role author_study_team_role, sr.eresearch_role author_eresearch_role,
        ca_author.current_appointments author_appointments,
        vestm.imported_team_member_user_name pi_user_name,
        ca_pi.current_appointments pi_appointments,
        sc.prior_created_count, sc.total_created_count, sc.member_of_other_studies_count,
        uld.login_days, TO_CHAR(uld.min_login_time, 'MM/DD/YYYY HH24:MI:SS.FF6') min_login_time, TO_CHAR(uld.max_login_time, 'MM/DD/YYYY HH24:MI:SS.FF6') max_login_time,
        spa.time_spent_on_study_info_page_ms,
        ROUND(
          (EXTRACT(DAY    FROM (spa.end_time - spa.start_time)) * 86400000) +
          (EXTRACT(HOUR   FROM (spa.end_time - spa.start_time)) * 3600000)  +
          (EXTRACT(MINUTE FROM (spa.end_time - spa.start_time)) * 60000)    +
          (EXTRACT(SECOND FROM (spa.end_time - spa.start_time)) * 1000)
        ) time_to_finish_adding_study_ms,
        spga.latency_ms, spga.source_size_chars,
        spga.source_type,
        lv.display_text  study_content_source,
        lv2.display_text llm_inferred_study_content_source,
        spga.study_content_source_other_value,
        spga.llm_suggested_study_content_source_other_value llm_inferred_study_content_source_other_value,
        spga.user_feedback_comments,
        spga.llm_suggestions, spga.selected_suggestions, spa.final_submission, spga.llm_metadata
   FROM study_posting_audit spa
   LEFT JOIN study_posting_generation_audit spga
          ON spa.id = spga.study_posting_audit_id
   LEFT JOIN study_posting_generation_audit_error spgae
          ON spga.id = spgae.study_posting_generation_audit_id
   LEFT JOIN lookup_value lv  ON lv.id  = spga.study_content_source_lv_id
   LEFT JOIN lookup_value lv2 ON lv2.id = spga.llm_suggested_study_content_source_lv_id
   LEFT JOIN study_stats ss   ON ss.study_num = spa.study_num
   LEFT JOIN stm_roles sr     ON sr.study_num = spa.study_num
                             AND sr.user_name = spa.user_name
   LEFT JOIN study_counts sc  ON sc.study_posting_audit_id = spa.id
   LEFT JOIN user_login_days uld ON uld.user_name = spa.user_name
   LEFT JOIN v_eres_study_team_member vestm
          ON vestm.imported_study_id = spa.study_num
         AND vestm.role = 'PI'
   LEFT JOIN attempt_author_appointments ca_author ON ca_author.study_posting_audit_id = spa.id
   LEFT JOIN attempt_pi_appointments    ca_pi     ON ca_pi.study_posting_audit_id    = spa.id
 order by spa.start_time, spa.user_name;
