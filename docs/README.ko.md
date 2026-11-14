# sensei-for-evidence 한국어 안내

질문 정의부터 검색·선별·추출·근거 검토·후속 작업까지 연결하는 추적 가능한 연구 워크플로입니다.
영어 README는 [../README.md](../README.md)에 있습니다. 코드, 명령, 파일 이름, 필드 이름과
`NOT_READY` 같은 상태 라벨은 원문 그대로 씁니다.

**검색이 끝났다는 것은 근거가 충분하다는 뜻이 아닙니다.** 일관된 파일, 완료로 표시된
작업 패키지, 재현 가능한 번들은 모두 기록이지, 완료된 과학적 연구가 아닙니다.

## 목적

이 저장소는 근거 기반 연구를 **추적 가능한 기록**으로 남기기 위한 표준 라이브러리 전용
Python 도구 모음입니다. 사람이 작성해 넘겨 준 데이터(검색 계획과 영수증, 서지 파일,
선별 결정, 보고서, 결과 행, 가이드라인·개발 맥락, 평가, 종합 진술, 독립 반론, 작업
패키지)를 서로 대조해 원장(ledger), 검토 대기열, 결정적(deterministic) 번들, 버전 비교
결과로 정리합니다. 도구는 무엇이 빠졌는지, 무엇이 오래되어(stale) 다시 봐야 하는지,
무엇이 아직 검토되지 않았는지를 드러낼 뿐, 어떤 판단도 대신하지 않습니다.

워크플로 자체는 [SKILL.md](../SKILL.md)의 열 단계(질문과 범위 확정, 중립적 탐색, 프로토콜
고정, 검색 기록, 정규화, 평가, 범위 안의 종합, 독립 반론, 충분성과 결론 준비도의 분리
평가, 인용·산출물 검증)로 정리되어 있고, 설계 원칙과 방법론적 경계는
[ARCHITECTURE.md](ARCHITECTURE.md)에 있습니다.

## 공개 범위

- 공개된 것: 일반화된 프레임워크 코드, 문서, 전부 가상(synthetic)으로 만든 예제와 테스트,
  빈 기록 템플릿, 에이전트 지침, 공개 점검 스크립트. 공개 파일 목록과 각 파일의 SHA-256은
  `PUBLICATION_MANIFEST.json`에 묶여 있고 `verify_manifest.py`가 확인합니다.
- 공개되지 않은 것: 실제 연구 코퍼스, 대화 기록, 개인별 페르소나 패키지, 실험·근거
  데이터베이스, 논문·도서·그림 원문, 비공개 설정, 자격 증명, 로그, 비공개 Git 이력.
  자세한 내용은 [PUBLICATION.md](../PUBLICATION.md)와 [SECURITY.md](../SECURITY.md)에 있습니다.
- 라이선스는 아직 선택되지 않았습니다. 공개되어 있다는 사실만으로 복사·수정·재배포 권한이
  생기지 않습니다([RIGHTS.md](../RIGHTS.md)).
- 네트워크 요청은 명시적으로 호출하는 `pubmed_discovery.py fetch`와 `pubmed_metadata.py fetch`
  두 경로만 수행하며, 그 전에 미리보기 해시가 정확히 일치해야 합니다. 그 밖의 모든 처리는
  오프라인이고, API 키나 계정 정보는 지원하지 않습니다.

## 설치와 빠른 시작

Python 3.10 이상이면 되고, 서드파티 패키지는 필요 없습니다. 저장소를 받은 뒤 저장소 루트에서
실행합니다. 아래 명령은 영어 README의 Quick start와 같습니다.

```sh
python sensei.py check
python review_handoff.py examples/claim-comparison.json --work-package WP-TRANSLATION --text
python research_status.py examples/review-demo.json --text
python evidence_workflow.py examples/review-demo.json
python prisma_reports.py examples/review-demo.json
python research_bundle.py create examples/review-demo.json ../synthetic-review.zip
python research_bundle.py verify ../synthetic-review.zip
python compare_runs.py examples/review-demo.json examples/review-demo.json
```

전체 검증(수 분 소요): `python -m unittest discover -v`를 실행하고
`python audit_publication.py`와 `python verify_manifest.py`도 실행하세요.
`check`는 저장소 파일·문법·가상 상태만 확인하며 전체 테스트, CI 매트릭스나 연구 검증을
대신하지 않습니다. [빠른 저장소 점검](CHECKOUT_CHECK.md)을 참고하세요.

자기 파일은 어느 디렉터리에서든
`python PATH/TO/sensei-for-evidence/research_status.py ./my-protocol.json` 또는
`python PATH/TO/sensei-for-evidence/sensei.py run research_status.py ./my-protocol.json`으로
처리할 수 있습니다. 상대 입력·출력 경로는 현재 작업 디렉터리 기준입니다. 안내 문서의
예제 경로는 저장소 루트 기준이므로 문서의 리허설은 루트에서 실행하세요.

ZIP 출력 경로는 미리 존재하면 안 됩니다. 실제 연구 입력과 생성된 번들은 이 공개 저장소
바깥에 두세요. 번들은 넘겨 준 데이터를 가공 없이 그대로 보존합니다. 위 명령은 어떤
업로드나 외부 요청도 하지 않습니다.

예제 `examples/review-demo.json`은 전부 가상의 데이터이며 의도적으로 미완성 상태입니다.
식별된 레코드 두 건, 포함된 보고서/연구 한 건, 결과 행 두 건이 있고, 계획된 출처 하나가
빠져 있으며, 맥락 검토 하나가 대기 중이고, 결과 하나에는 평가가 기록되어 있지 않습니다.
`WP-TRANSLATION`은 끝나지 않은 `WP-MECHANISM`에 의존합니다. 번들 검증이 통과해도 과학적
준비도 경계는 모두 닫힌 채로 남습니다. 이 예제는 기록 방식과 테스트 동작을 보여 줄 뿐,
연구 결과나 실험·임상 권고가 아닙니다.

처음이라면 다음 순서를 권합니다.

1. [FIRST_RUN.md](FIRST_RUN.md): 질문 선언과 모의 영수증에서 시작해 검토, PRISMA 집계, 맥락
   작업, 검증된 번들까지 이어지는 11개의 테스트된 명령.
2. [BATCH_TO_EVIDENCE.md](BATCH_TO_EVIDENCE.md)와 [SECOND_SEARCH_CONTINUATION.md](SECOND_SEARCH_CONTINUATION.md):
   실제 서지 파일(NBIB) 두 개를 대조·선별·보고서·결과까지 끌고 가는 리허설과, 계획된 두 번째
   검색을 덧붙이는 이어가기.
3. [OPERATOR_HANDOFF.md](OPERATOR_HANDOFF.md): 사람이 해야 할 일의 대기열과 모든 입력 경로를
   실행 없이 한 장으로 보여 주는 운영자 인계 시트.

안내 문서의 명령 블록에 나오는 `OUTPUT`은 저장소 바깥에 미리 만들어 둔 빈 디렉터리를
뜻합니다. 주요 리허설 문서의 명령 블록은 테스트가 적힌 그대로 실행하므로, 문서의 명령은
그대로 따라 할 수 있습니다.

## 주요 명령

모든 스크립트와 하위 명령의 정확한 사용법은 [COMMANDS.md](COMMANDS.md)에, 단계별 설명은
[WORKFLOWS.md](WORKFLOWS.md)에 있습니다. 출력 옵션은 항상 새 파일을 만들며 이미 있는 경로를
덮어쓰지 않습니다. `--text`를 붙이면 읽기 전용 요약을, 붙이지 않으면 JSON을 출력합니다.

명령줄 스크립트는 모두 저장소 루트의 모듈이고, 가상 테스트 묶음은 `tests/` 패키지에 있습니다.
`python sensei.py list`는 루트 스크립트와 운영자 인계 카탈로그의 입력 경로를 실행 없이 한 번에
보여 주고, `python sensei.py run <스크립트> [인자...]`는 그 스크립트를
`python <스크립트> [인자...]`와 똑같이 실행합니다.

| 단계 | 명령 | 하는 일 |
|---|---|---|
| 시작·상태 | `review_handoff.py`, `research_status.py` | 사람이 처리할 대기열과 입력 위치를 보여 주는 읽기 전용 인계 시트, 기계적 검토 대기열 요약 |
| 대조·집계 | `evidence_workflow.py`, `prisma_reports.py`, `prisma_audit.py` | 검색→선별→결과→작업 대조, 보고서/전문 단계 집계, PRISMA 지향 집계 내보내기 |
| 검색 계획·영수증 | `search_manifest.py`, `receipt_intake.py`, `offline_adapter.py` | 질의와 영수증 명세 고정, 수동 영수증 입력 리허설, 검토 게이트가 있는 오프라인 모의 어댑터 |
| 서지 파일 수집 | `bibliographic_intake.py`, `nbib_intake.py`, `nbib_batch_intake.py`, `ris_intake.py`, `bibliographic_review.py` | CSV/NBIB/RIS 내보내기 파일을 바이트 그대로 보존한 뒤 명시적 동일성 판단으로 선별 대기열에 연결 |
| 선택적 PubMed | `pubmed_discovery.py`, `pubmed_metadata.py` | 미리보기 해시에 묶인 ESearch 식별자 탐색과 EFetch 제목·초록 수집. 유일한 네트워크 명령 |
| 선별 | `screening_review.py`, `screening_decision.py`, `screening_sheet.py` | 검토자 입장 기록과, 사람이 내린 선별 결정의 명시적 적용 |
| 보고서·전문 | `report_intake.py`, `report_retrieval.py`, `report_source_intake.py`, `report_source_check.py`, `report_review.py`, `report_decision.py`, `report_study_review.py`, `report_study_inventory.py`, `inventory_intake.py`, `report_study_inventory_review.py` | 보고서 등록, 입수 상태 갱신, 출처 선언과 로컬 바이트 확인, 전문 검토 입장과 결정, 보고서-연구 단위 입장과 서술적 목록 |
| 결과·조건 | `result_extraction.py`, `result_passage_check.py`, `result_intake.py`, `result_source_review.py`, `result_correction.py`, `condition_intake.py` | 빈 추출 워크시트, 원문 구절 대조, 수동 결과 입력, 출처 변동 비교, 문구 수정, 비임상 비교 조건 기록 |
| 맥락·평가 | `context_intake.py`, `work_context_intake.py`, `appraisal_intake.py`, `appraisal_source_review.py` | 가이드라인·개발 맥락 기록과 작업 배정, 평가 기록과 이후 맥락 변동 비교 |
| 종합·반론·준비도 | `synthesis_review.py`, `challenge_intake.py`, `readiness_review.py`, `readiness_intake.py` | 종합 진술 스냅숏, 독립 반론 기록, 결론 준비도 게이트 원장과 충분성·준비도 주장 기록 |
| 작업 패키지 | `work_review.py`, `source_work_intake.py`, `evidence_work_intake.py`, `work_completion_intake.py`, `artifact_review.py` | 작업 검토 패킷, 검토된 작업 제안과 완료 기록, 선택적 로컬 산출물 바이트 확인 |
| 번들·비교 | `research_bundle.py`, `*_bundle.py`, `compare_runs.py`, `validate_run.py` | 결정적 번들과 전환·수집 아카이브, 버전 비교, 상태 검증 |

입력 도구(`*_intake.py`)는 대부분 네 단계로 이루어집니다. `template`은 현재 프로토콜에 묶인
빈 후보 문서를 만들고, `target`은 사람이 채운 후보를 현재 프로토콜과 정확히 묶어 검토 대상을
만들고, `assemble`은 별도로 작성한 검토를 적용해 분리된 적용 기록을 만들고, `verify`는 그
기록을 원본 프로토콜에 다시 재생해 확인하며 `--protocol-output`으로 결과 프로토콜을 내보냅니다.
어느 단계도 결정이나 판단, 라벨을 대신 채우지 않습니다.

워크플로의 8단계와 9단계는 다음 두 도구로 기록합니다.

- 독립 반론: `challenge_intake.py`는 기존 종합 진술에 대한 반론을 기록합니다. 반론자 라벨은
  해당 진술에 기록된 검토자·입장 기록자·평가자 라벨과 달라야 하고(같으면 거부), 가장 강한
  대안 설명, 빠진 판별 근거, 인용 무결성 소견, 결론 폭, 결과(`SURVIVES`, `MATERIAL_GAP`,
  `UNRESOLVED`)를 사람이 직접 적습니다. `MATERIAL_GAP`은 기존 재개 작업이나 수정 메모를
  지정해야 합니다. 라벨이 다르다는 것은 독립성이 검증되었다는 뜻이 아니며, `SURVIVES`는
  증명이 아니고 `UNRESOLVED`는 결함이 아닙니다. [INDEPENDENT_CHALLENGE.md](INDEPENDENT_CHALLENGE.md)
- 결론 준비도: `readiness_review.py`는 넘겨 준 기록에서 열두 개의 기계적 게이트(검색 계획,
  검색, 선별, 보고서, 추출, 인용된 결과의 평가, 진술 검토, 인용, 반론 기록과 해소, 맥락,
  작업)를 열린 항목과 함께 보여 주고 그 원장의 해시를 계산합니다. `readiness_intake.py`는 그
  해시에 묶인 근거 충분성과 결론 준비도 주장을 따로 기록합니다. 게이트가 모두 닫혔다는 것은
  장부가 비었다는 뜻일 뿐 근거가 충분하다는 뜻이 아니며, 모든 도구의 기계적
  `conclusion_readiness`는 `NOT_READY`로 남습니다. [CONCLUSION_READINESS.md](CONCLUSION_READINESS.md)

## 경계와 하지 않는 것

- 문헌을 검색하지 않습니다. 예외는 위의 두 PubMed `fetch` 경로뿐이며, ESearch가 돌려주는
  것은 식별자이고 EFetch가 돌려주는 것은 제목·초록 후보입니다. 둘 다 읽은 논문, 선별된
  레코드, 추출된 결과가 아닙니다.
- 논문을 읽지 않고, 언어 모델을 호출하지 않으며, 출처·검색 페이지·검토자 주장을 인증하지
  않습니다. 해시는 동일성을 확인할 뿐 서명이 아닙니다.
- 과학적 평가, 메타분석, 임상 권고, 가이드라인 최신성 확인, 법적 의견(특허 FTO 포함)을
  수행하지 않습니다. 평가 점수나 합의를 추론하지 않고, 검토자 입장을 투표로 세지 않습니다.
- 이미 있는 검토, 평가, 완료 주장을 자동으로 갱신하지 않습니다. 출처가 바뀌면 관련 주장을
  stale로 표시할 뿐이며, 사람이 다시 보고 새로 기록해야 합니다.
- 완료된 작업 패키지, 통과한 번들 검증, 닫힌 게이트, 기록된 `READY` 주장은 모두 사람이
  넘겨 준 주장 또는 장부 상태입니다. 모든 출력에서 census는 `NOT_ESTABLISHED`, 기계적 결론
  준비도는 `NOT_READY`로 남습니다.
- 예제 데이터는 전부 가상이며 어떤 실제 연구도 검증하지 않았습니다. 실제 입력과 생성된
  출력은 저장소 바깥에 두고, 자세한 공개 경계는 [PUBLICATION.md](../PUBLICATION.md),
  [SECURITY.md](../SECURITY.md), [RIGHTS.md](../RIGHTS.md)를 따릅니다.

## 문서 색인

- 시작과 참조: [FIRST_RUN.md](FIRST_RUN.md) 첫 오프라인 실행 ·
  [OPERATOR_HANDOFF.md](OPERATOR_HANDOFF.md) 운영자 인계 시트 ·
  [BATCH_TO_EVIDENCE.md](BATCH_TO_EVIDENCE.md) NBIB 파일에서 근거까지 리허설 ·
  [SECOND_SEARCH_CONTINUATION.md](SECOND_SEARCH_CONTINUATION.md) 두 번째 검색 이어가기 ·
  [COMMANDS.md](COMMANDS.md) 명령 참조 · [WORKFLOWS.md](WORKFLOWS.md) 단계별 설명 ·
  [USAGE.md](USAGE.md) 상세 사용법과 호환성 · [ARCHITECTURE.md](ARCHITECTURE.md) 설계와 경계 ·
  [VALIDATION_HISTORY.md](VALIDATION_HISTORY.md) 검증 기록 이력
- 검색 계획·영수증·출처 작업: [SEARCH_MANIFEST.md](SEARCH_MANIFEST.md) ·
  [RECEIPT_INTAKE.md](RECEIPT_INTAKE.md) · [ADAPTER_CONTRACT.md](ADAPTER_CONTRACT.md) ·
  [SOURCE_REVIEW_WORK.md](SOURCE_REVIEW_WORK.md) · [SOURCE_WORK_INTAKE.md](SOURCE_WORK_INTAKE.md) ·
  [SOURCE_CONTEXTS.md](SOURCE_CONTEXTS.md) · [WORK_DOCUMENT_SOURCES.md](WORK_DOCUMENT_SOURCES.md)
- 서지 파일과 수집: [BIBLIOGRAPHIC_INTAKE.md](BIBLIOGRAPHIC_INTAKE.md) ·
  [PUBMED_NBIB_INTAKE.md](PUBMED_NBIB_INTAKE.md) · [PUBMED_NBIB_BATCH.md](PUBMED_NBIB_BATCH.md) ·
  [RIS_INTAKE.md](RIS_INTAKE.md) · [BIBLIOGRAPHIC_REVIEW.md](BIBLIOGRAPHIC_REVIEW.md) ·
  [COLLECTION_BUNDLES.md](COLLECTION_BUNDLES.md) · [BATCH_COLLECTION_BUNDLES.md](BATCH_COLLECTION_BUNDLES.md) ·
  [NATIVE_COLLECTION_BUNDLES.md](NATIVE_COLLECTION_BUNDLES.md) · [PUBMED_DISCOVERY.md](PUBMED_DISCOVERY.md) ·
  [PUBMED_METADATA.md](PUBMED_METADATA.md)
- 선별과 보고서: [SCREENING_REVIEWS.md](SCREENING_REVIEWS.md) · [SCREENING_DECISIONS.md](SCREENING_DECISIONS.md) ·
  [PRISMA_AUDIT.md](PRISMA_AUDIT.md) · [MULTI_STUDY_REPORTS.md](MULTI_STUDY_REPORTS.md) ·
  [MANUAL_REPORT_INTAKE.md](MANUAL_REPORT_INTAKE.md) · [REPORT_RETRIEVAL_UPDATES.md](REPORT_RETRIEVAL_UPDATES.md) ·
  [MANUAL_SOURCE_DECLARATIONS.md](MANUAL_SOURCE_DECLARATIONS.md) · [REPORT_SOURCE_CHECK.md](REPORT_SOURCE_CHECK.md) ·
  [REPORT_REVIEWS.md](REPORT_REVIEWS.md) · [REPORT_DECISIONS.md](REPORT_DECISIONS.md) ·
  [REPORT_STUDY_REVIEWS.md](REPORT_STUDY_REVIEWS.md) · [REPORT_STUDY_INVENTORY.md](REPORT_STUDY_INVENTORY.md) ·
  [MANUAL_INVENTORY_INTAKE.md](MANUAL_INVENTORY_INTAKE.md) · [INVENTORY_CANDIDATE_REVIEWS.md](INVENTORY_CANDIDATE_REVIEWS.md) ·
  [REPORT_TRANSITION_BUNDLES.md](REPORT_TRANSITION_BUNDLES.md)
- 결과와 조건: [EXTRACTION_WORKSHEETS.md](EXTRACTION_WORKSHEETS.md) · [RESULT_PASSAGE_CHECK.md](RESULT_PASSAGE_CHECK.md) ·
  [MANUAL_RESULT_INTAKE.md](MANUAL_RESULT_INTAKE.md) · [RESULT_SOURCE_REVIEW.md](RESULT_SOURCE_REVIEW.md) ·
  [RESULT_CORRECTIONS.md](RESULT_CORRECTIONS.md) · [MANUAL_CONDITION_INTAKE.md](MANUAL_CONDITION_INTAKE.md) ·
  [EXPERIMENT_CONDITIONS.md](EXPERIMENT_CONDITIONS.md) · [OUTCOME_STATISTICS.md](OUTCOME_STATISTICS.md) ·
  [CLAIM_COMPARISON.md](CLAIM_COMPARISON.md) · [EXTRACTION_TRANSITION_BUNDLES.md](EXTRACTION_TRANSITION_BUNDLES.md)
- 맥락·평가·종합·준비도: [MANUAL_CONTEXT_INTAKE.md](MANUAL_CONTEXT_INTAKE.md) · [WORK_CONTEXT_INTAKE.md](WORK_CONTEXT_INTAKE.md) ·
  [CONTEXT_AMENDMENTS.md](CONTEXT_AMENDMENTS.md) · [MANUAL_APPRAISAL_INTAKE.md](MANUAL_APPRAISAL_INTAKE.md) ·
  [APPRAISAL_SOURCE_REVIEW.md](APPRAISAL_SOURCE_REVIEW.md) · [APPRAISAL_TRANSITION_BUNDLES.md](APPRAISAL_TRANSITION_BUNDLES.md) ·
  [SYNTHESIS_REVIEW.md](SYNTHESIS_REVIEW.md) · [INDEPENDENT_CHALLENGE.md](INDEPENDENT_CHALLENGE.md) ·
  [CONCLUSION_READINESS.md](CONCLUSION_READINESS.md)
- 계획·작업·완료: [WORK_REVIEW.md](WORK_REVIEW.md) · [WORK_NAVIGATION.md](WORK_NAVIGATION.md) ·
  [PREREQUISITE_REVIEW.md](PREREQUISITE_REVIEW.md) · [PLANNING_ASSERTIONS.md](PLANNING_ASSERTIONS.md) ·
  [PLANNING_RATIONALE_LINKS.md](PLANNING_RATIONALE_LINKS.md) · [AMENDMENT_NOTES.md](AMENDMENT_NOTES.md) ·
  [COMPLETION_BINDING.md](COMPLETION_BINDING.md) · [COMPLETION_COMPARISON.md](COMPLETION_COMPARISON.md) ·
  [EVIDENCE_WORK_INTAKE.md](EVIDENCE_WORK_INTAKE.md) · [WORK_COMPLETION_INTAKE.md](WORK_COMPLETION_INTAKE.md) ·
  [WORK_TRANSITION_BUNDLES.md](WORK_TRANSITION_BUNDLES.md) · [LOCAL_ARTIFACT_REVIEW.md](LOCAL_ARTIFACT_REVIEW.md)
- 저장소 수준 문서: [SKILL.md](../SKILL.md) 에이전트용 워크플로 지침 · [VALIDATION.md](../VALIDATION.md) 현재 검증 스냅숏 ·
  [PUBLICATION.md](../PUBLICATION.md) 공개 범위 · [SECURITY.md](../SECURITY.md) 보안 경계 · [RIGHTS.md](../RIGHTS.md) 권리

이전 번들이나 기록의 구현 해시가 달라졌다면
[구현 리비전 검사](IMPLEMENTATION_REVISIONS.md)를 참고하세요.
`implementation_check.py inspect`는 기록된 파일 바이트만 비교하며, 과거 코드를
실행하거나 연구 결과를 검증하지 않습니다.

## 공급된 개수의 CSV 대응표

[PRISMA 지향 개수 대응표](PRISMA_FLOW_TEMPLATE.md)는 검색 입력 인덱스별로
명시한 갈래와 기존 감사 원장의 개수를 새 CSV 파일에 기록합니다. 공식 PRISMA
템플릿이나 외부 그림 도구의 가져오기 형식이 아닙니다. 정확 ID 반복과 선별 개수는
기본적으로 비우며, 누락·대기 상태와 출처별 문제는 stdout 영수증에 남깁니다.

## 상태를 Markdown으로 저장

[공유용 상태 보기](SHAREABLE_VIEWS.md)의 `views_export.py status`는 기존
상태 결과와 모든 대기열을 새 Markdown 파일에 보존합니다. 미공급과 0을 구분하고,
공급 문자열은 인용된 코드 블록 안에만 둡니다. stdout에는 파일 크기·해시와
경계 문구가 담긴 영수증만 출력합니다. 연구 준비도 판정이나 PRISMA 도식이 아니며,
실제 연구 정보는 비공개로 유지하고 승인 없이 공유하지 마세요.

## 공급 개수의 흐름 텍스트

`views_export.py flow`는 [공급자료 회계 흐름](ACCOUNTING_FLOW.md)을 Mermaid
텍스트로 저장합니다. 기존 감사의 분할별 그룹과 서로 다른 단위의 점선 연결만
보여주며, 공급 문자열은 포함하지 않습니다. 미공급은 0이 아니고 반복 노드는
합산하지 않습니다. 공식 PRISMA 도식·준비도 인증이나 렌더러가 아닙니다.

## URL이 비어 있는 CSV 가져오기

모든 행에 값이 있는 키 열이 있다면 기존 명령에서 `--id-column Key
--locator-column Key`처럼 같은 열을 명시할 수 있습니다. 모든 행에서 키를
그대로 사용하며 빈 URL/DOI 셀도 원래 값으로 보존합니다. locator는 열거나
인증하지 않는 텍스트입니다. 중복 키는 별도 출현으로 남고 빈 키는 거부합니다.
[합성 예제로 실행하는 안내](CSV_KEY_MAPPING.md)는 미작성 검토 양식에서
멈추며 동일성 판정·선별·검색 완료를 자동으로 인정하지 않습니다.

## 레코드 CSV 내보내기

`python views_export.py records PROTOCOL --output NEW.csv`는 기존 감사 원장의
레코드·검색 출현·보고서·결과 연결을 별도 CSV로 저장합니다. 검색 인덱스가 기준이며
검색 ID는 표시용입니다. 보고서의 연구 ID와 결과의 연구 ID를 구분하고, 미공급
단계와 빈 목록을 구별합니다. 검토 비교 단서는 판정이 아닙니다. 출력은 비식별화되지
않으므로 공개 저장소 밖에 보관하고 공유 권한을 확인하세요. 영수증에 경계 문구와
해시가 남으며 `NOT_ESTABLISHED`/`NOT_READY`는 유지됩니다.
[실행 예제와 열 설명](RECORDS_CSV.md)을 참고하세요.

## 명시적 RIS 연속 줄 방언

[별도 가이드](RIS_CONTINUATION_INTAKE.md)는 태그 없는 연속 줄과 빈 문단의
문법을 명시적으로 선언하며 원본 바이트를 보존합니다. 기존 strict RIS와
native 아카이브는 바꾸지 않고, 새 래퍼는 별도로 보관합니다. 네 명령 예제는
빈 검토 양식에서 멈추며 동일성 판단이나 연구 결론을 만들지 않습니다.

## 빈 선별 입장 CSV

[전사용 CSV 내보내기](SCREENING_SHEETS.md)는 기존 source hash와 원본 식별자를
보존하고 사람 작성 열은 모두 비워 둡니다. 선택한 보존 원문 열은 읽기 전용
표시로만 제공하며, CSV 내보내기는 선별 수행·결정·작성 시트 입수가 아닙니다.
실제 자료는 공개 저장소 밖에 보관하고 오래된 hash를 새 값으로 갈아 끼우지 마세요.

## 로컬 HTML 검토

[읽기 전용 HTML 안내](REVIEW_VIEWS.md)는 게이트·큐·공급된 집계·진술을 보여 줍니다. 승인이나 연구보고서가 아니며 실제 출력은 공개 저장소 밖에 보관합니다.

[네이티브 레코드 재내보내기](COLLECTION_EXPORT.md)는 공급된 선별결정에 맞는 RIS/NBIB occurrence를 재생성하고 검증합니다. 중복 제거·전문 적격성 판정이 아니며 실제 파일은 공개 저장소 밖에 보관합니다.
