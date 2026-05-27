import { useState } from 'react';

type ScheduleStatus = '예정' | '승인' | '완료' | '확인';

interface MaintenanceTask {
  id: number;
  title: string;
  siteArea: string;
  vendor: string;
  scheduledAt: string;
  status: ScheduleStatus;
  cost: string;
  priority: '높음' | '보통' | '낮음';
  assignee: string;
  evidence: string;
  decision: string;
}

interface PlantDashboard {
  name: string;
  capacity: string;
  state: '정상' | '주의';
  output: string;
  connection: string;
  lastSeen: string;
  risk: string;
  statCards: Array<{ label: string; value: string; detail: string; trend: string }>;
  secondaryMetrics: Array<[string, string, string]>;
  hourlyGeneration: number[];
  generationSummary: [string, string, string];
  weatherImpact: Array<{ label: string; value: string; delta: string }>;
  inverterRows: Array<{ name: string; output: string; efficiency: string; temp: string; status: '정상' | '주의' }>;
  stringPerformance: Array<{ name: string; value: number; loss: string; tone: string }>;
  anomalyRows: Array<{ target: string; severity: '높음' | '중간' | '낮음'; cause: string; evidence: string; action: string }>;
  degradation: Array<[string, string, string]>;
  tasks: MaintenanceTask[];
}

const statusOrder: ScheduleStatus[] = ['예정', '승인', '완료', '확인'];

const sidebarSections = [
  { label: '운영 개요', count: 'LIVE' },
  { label: '정밀 모니터링', count: '24' },
  { label: '이상 탐지', count: '2' },
  { label: '관리 일정', count: '4' },
  { label: '정산/리포트', count: '5월' },
];

const plantDashboards: PlantDashboard[] = [
  {
    name: '화성 제1공장',
    capacity: '2.8MWp',
    state: '정상',
    output: '2.14MW',
    connection: '계통연계 정상',
    lastSeen: '32초 전',
    risk: '18%',
    statCards: [
      { label: '현재 출력', value: '2.14 MW', detail: '설비용량 대비 76.4%', trend: '+4.8%' },
      { label: '금일 발전량', value: '12.8 MWh', detail: '예측 13.4 MWh', trend: '95.5%' },
      { label: '월 누적 발전량', value: '286 MWh', detail: '전월 동기 대비', trend: '+8.1%' },
      { label: '예상 정산액', value: '4,432만원', detail: 'SMP+REC 기준', trend: '+312만원' },
    ],
    secondaryMetrics: [
      ['성능비 PR', '83.7%', '목표 82.0% 대비 양호'],
      ['가동률', '98.9%', 'INV-03 저효율 반영'],
      ['CO₂ 절감', '5.7t', '금일 누적 기준'],
    ],
    hourlyGeneration: [38, 54, 76, 93, 114, 121, 118, 105, 92, 74, 51, 32],
    generationSummary: ['실측 12.8MWh', '예측 13.4MWh', '편차 -4.5%'],
    weatherImpact: [
      { label: '일사량', value: '742 W/m²', delta: '+6.2%' },
      { label: '모듈 온도', value: '43.8°C', delta: '-2.9%' },
      { label: '풍속', value: '3.1 m/s', delta: '+0.8%' },
      { label: '구름량', value: '18%', delta: '-4.1%' },
    ],
    inverterRows: [
      { name: 'INV-01', output: '228kW', efficiency: '98.4%', temp: '41°C', status: '정상' },
      { name: 'INV-02', output: '219kW', efficiency: '97.9%', temp: '42°C', status: '정상' },
      { name: 'INV-03', output: '174kW', efficiency: '92.1%', temp: '58°C', status: '주의' },
      { name: 'INV-04', output: '231kW', efficiency: '98.6%', temp: '40°C', status: '정상' },
    ],
    stringPerformance: [
      { name: 'S-01', value: 98, loss: '0.4%', tone: 'bg-emerald-400' },
      { name: 'S-06', value: 95, loss: '1.1%', tone: 'bg-emerald-400' },
      { name: 'S-12', value: 91, loss: '2.8%', tone: 'bg-lime-300' },
      { name: 'S-17', value: 72, loss: '22.8%', tone: 'bg-red-400' },
      { name: 'S-21', value: 87, loss: '5.7%', tone: 'bg-yellow-300' },
      { name: 'S-28', value: 94, loss: '1.6%', tone: 'bg-emerald-400' },
    ],
    anomalyRows: [
      {
        target: '스트링 S-17',
        severity: '높음',
        cause: '커넥터 접촉 저항 또는 부분 음영',
        evidence: '동일 방위 스트링 평균 대비 -22.8%',
        action: '현장 점검 및 IV curve 측정',
      },
      {
        target: '인버터 INV-03',
        severity: '중간',
        cause: '냉각팬 회전수 저하',
        evidence: '내부 온도 58°C, 효율 92.1%',
        action: '냉각팬 교체 작업 승인',
      },
      {
        target: 'A동 북측 4열',
        severity: '낮음',
        cause: '오염 누적',
        evidence: '최근 14일 PR 1.9%p 하락',
        action: '세척 일정 확정 대기',
      },
    ],
    degradation: [
      ['PR 추세', '-1.2%p', '90일'],
      ['오염 손실', '2.4%', '세척 전'],
      ['온도 손실', '5.8%', '금일'],
      ['차단 손실', '0.6%', '계통'],
    ],
    tasks: [
      {
        id: 1,
        title: 'A동 지붕 패널 세척',
        siteArea: 'A동 1.2MWp',
        vendor: '해솔 O&M',
        scheduledAt: '2026-05-29 09:00',
        status: '예정',
        cost: '320만원',
        priority: '보통',
        assignee: '설비운영팀 김민수',
        evidence: '작업 전 오염도 사진 18건 수집',
        decision: '입찰가 3개 업체 비교 후 해솔 O&M 추천',
      },
      {
        id: 2,
        title: '3번 인버터 냉각팬 교체',
        siteArea: 'B동 인버터실',
        vendor: '그리드케어',
        scheduledAt: '2026-05-28 14:00',
        status: '승인',
        cost: '86만원',
        priority: '높음',
        assignee: '전기안전관리자 박서연',
        evidence: '열화상 점검 리포트 및 부품 견적 첨부',
        decision: '온도 상승 지속으로 48시간 내 교체 승인',
      },
      {
        id: 3,
        title: '스트링 S-17 커넥터 재체결',
        siteArea: 'C동 남측',
        vendor: 'PV 메이트',
        scheduledAt: '2026-05-26 11:30',
        status: '완료',
        cost: '42만원',
        priority: '높음',
        assignee: '현장대리인 이지훈',
        evidence: '완료 사진 9건, 발전량 회복 그래프 제출',
        decision: '작업 전후 스트링 전류 회복 확인 필요',
      },
      {
        id: 4,
        title: '분기 정기 안전 점검',
        siteArea: '전체 설비',
        vendor: '한국전기안전 파트너스',
        scheduledAt: '2026-05-24 10:00',
        status: '확인',
        cost: '190만원',
        priority: '낮음',
        assignee: '운영총괄 최유진',
        evidence: '절연저항 측정표와 담당자 확인 완료',
        decision: '법정 점검 기록 보관 완료',
      },
    ],
  },
  {
    name: '평택 물류센터',
    capacity: '1.1MWp',
    state: '주의',
    output: '0.72MW',
    connection: '계통전압 변동 감시',
    lastSeen: '1분 08초 전',
    risk: '31%',
    statCards: [
      { label: '현재 출력', value: '0.72 MW', detail: '설비용량 대비 65.5%', trend: '-6.3%' },
      { label: '금일 발전량', value: '4.1 MWh', detail: '예측 5.0 MWh', trend: '82.0%' },
      { label: '월 누적 발전량', value: '96 MWh', detail: '전월 동기 대비', trend: '-3.4%' },
      { label: '예상 정산액', value: '1,486만원', detail: 'SMP+REC 기준', trend: '-74만원' },
    ],
    secondaryMetrics: [
      ['성능비 PR', '76.8%', '목표 81.0% 대비 낮음'],
      ['가동률', '94.2%', 'PCS 통신 지연 반영'],
      ['CO₂ 절감', '1.9t', '금일 누적 기준'],
    ],
    hourlyGeneration: [22, 31, 43, 51, 58, 61, 56, 49, 44, 35, 25, 15],
    generationSummary: ['실측 4.1MWh', '예측 5.0MWh', '편차 -18.0%'],
    weatherImpact: [
      { label: '일사량', value: '615 W/m²', delta: '-3.8%' },
      { label: '모듈 온도', value: '46.5°C', delta: '-4.6%' },
      { label: '풍속', value: '1.8 m/s', delta: '-1.2%' },
      { label: '구름량', value: '34%', delta: '-8.5%' },
    ],
    inverterRows: [
      { name: 'INV-A', output: '182kW', efficiency: '96.8%', temp: '44°C', status: '정상' },
      { name: 'INV-B', output: '156kW', efficiency: '93.4%', temp: '55°C', status: '주의' },
      { name: 'INV-C', output: '171kW', efficiency: '96.1%', temp: '43°C', status: '정상' },
      { name: 'PCS-01', output: '대기', efficiency: '통신 지연', temp: '38°C', status: '주의' },
    ],
    stringPerformance: [
      { name: 'R-02', value: 94, loss: '1.3%', tone: 'bg-emerald-400' },
      { name: 'R-08', value: 82, loss: '8.9%', tone: 'bg-yellow-300' },
      { name: 'R-11', value: 78, loss: '13.4%', tone: 'bg-yellow-300' },
      { name: 'R-14', value: 69, loss: '25.2%', tone: 'bg-red-400' },
      { name: 'R-19', value: 88, loss: '5.1%', tone: 'bg-lime-300' },
      { name: 'R-22', value: 90, loss: '3.4%', tone: 'bg-lime-300' },
    ],
    anomalyRows: [
      {
        target: '루프 R-14',
        severity: '높음',
        cause: '물류센터 환기 덕트 음영',
        evidence: '10:40 이후 동일 패턴 반복, 손실 25.2%',
        action: '음영 시간대 재배치 검토',
      },
      {
        target: 'INV-B',
        severity: '중간',
        cause: '온도 상승 및 효율 저하',
        evidence: '효율 93.4%, 내부 온도 55°C',
        action: '필터 청소 및 냉각팬 점검',
      },
      {
        target: 'PCS-01',
        severity: '중간',
        cause: '통신 게이트웨이 지연',
        evidence: '최근 30분 데이터 누락 4회',
        action: 'LTE 라우터 재시작',
      },
    ],
    degradation: [
      ['PR 추세', '-3.8%p', '90일'],
      ['오염 손실', '3.1%', '세척 필요'],
      ['온도 손실', '6.4%', '금일'],
      ['차단 손실', '1.8%', '전압 변동'],
    ],
    tasks: [
      {
        id: 101,
        title: '환기 덕트 음영 영향 점검',
        siteArea: '서측 루프 R-14',
        vendor: '솔라뷰 엔지니어링',
        scheduledAt: '2026-05-28 10:00',
        status: '예정',
        cost: '65만원',
        priority: '높음',
        assignee: '물류설비팀 한지아',
        evidence: '10분 단위 스트링 손실 리포트 첨부',
        decision: '드론 촬영 후 구조물 간섭 여부 확인',
      },
      {
        id: 102,
        title: 'INV-B 필터 및 냉각팬 점검',
        siteArea: '동측 전기실',
        vendor: '그리드케어',
        scheduledAt: '2026-05-27 16:00',
        status: '승인',
        cost: '58만원',
        priority: '높음',
        assignee: '전기안전관리자 박서연',
        evidence: '열화상 이미지 6건, 온도 로그 48시간',
        decision: '효율 저하가 정산 손실로 이어져 당일 조치 승인',
      },
      {
        id: 103,
        title: '통신 게이트웨이 교체',
        siteArea: 'PCS-01 통신반',
        vendor: '넷에너지',
        scheduledAt: '2026-05-30 13:30',
        status: '예정',
        cost: '34만원',
        priority: '보통',
        assignee: 'IT운영팀 오세훈',
        evidence: '데이터 누락 로그와 라우터 상태 캡처',
        decision: '임시 재시작 후 재발 시 장비 교체',
      },
    ],
  },
  {
    name: '아산 지붕형',
    capacity: '680kWp',
    state: '정상',
    output: '512kW',
    connection: '자가소비 우선 운전',
    lastSeen: '45초 전',
    risk: '9%',
    statCards: [
      { label: '현재 출력', value: '512 kW', detail: '설비용량 대비 75.3%', trend: '+2.1%' },
      { label: '금일 발전량', value: '2.9 MWh', detail: '예측 3.0 MWh', trend: '96.7%' },
      { label: '월 누적 발전량', value: '64 MWh', detail: '전월 동기 대비', trend: '+5.6%' },
      { label: '전력비 절감', value: '812만원', detail: '자가소비 78%' , trend: '+46만원' },
    ],
    secondaryMetrics: [
      ['성능비 PR', '84.9%', '목표 82.5% 대비 양호'],
      ['가동률', '99.4%', '알람 없음'],
      ['CO₂ 절감', '1.3t', '금일 누적 기준'],
    ],
    hourlyGeneration: [12, 18, 28, 39, 46, 51, 52, 47, 39, 30, 20, 10],
    generationSummary: ['실측 2.9MWh', '예측 3.0MWh', '편차 -3.3%'],
    weatherImpact: [
      { label: '일사량', value: '705 W/m²', delta: '+4.4%' },
      { label: '모듈 온도', value: '41.2°C', delta: '-1.8%' },
      { label: '풍속', value: '3.8 m/s', delta: '+1.5%' },
      { label: '구름량', value: '12%', delta: '-2.6%' },
    ],
    inverterRows: [
      { name: 'INV-1F', output: '128kW', efficiency: '98.7%', temp: '39°C', status: '정상' },
      { name: 'INV-2F', output: '126kW', efficiency: '98.5%', temp: '40°C', status: '정상' },
      { name: 'INV-3F', output: '131kW', efficiency: '98.9%', temp: '38°C', status: '정상' },
      { name: 'INV-4F', output: '127kW', efficiency: '98.6%', temp: '39°C', status: '정상' },
    ],
    stringPerformance: [
      { name: 'A-01', value: 99, loss: '0.2%', tone: 'bg-emerald-400' },
      { name: 'A-04', value: 97, loss: '0.8%', tone: 'bg-emerald-400' },
      { name: 'A-09', value: 96, loss: '1.0%', tone: 'bg-emerald-400' },
      { name: 'B-02', value: 93, loss: '2.2%', tone: 'bg-lime-300' },
      { name: 'B-07', value: 95, loss: '1.4%', tone: 'bg-emerald-400' },
      { name: 'B-12', value: 94, loss: '1.9%', tone: 'bg-emerald-400' },
    ],
    anomalyRows: [
      {
        target: 'B-02 스트링',
        severity: '낮음',
        cause: '난간 근접부 아침 음영',
        evidence: '08:00-09:10 구간 출력 6.8% 낮음',
        action: '다음 정기 점검 때 음영 마킹',
      },
      {
        target: '접속반 JB-2',
        severity: '낮음',
        cause: '단자함 습도 상승',
        evidence: '상대습도 72%, 임계 80% 미만',
        action: '실리카겔 교체 예약',
      },
    ],
    degradation: [
      ['PR 추세', '+0.3%p', '90일'],
      ['오염 손실', '1.1%', '관찰'],
      ['온도 손실', '4.9%', '금일'],
      ['차단 손실', '0.0%', '없음'],
    ],
    tasks: [
      {
        id: 201,
        title: '접속반 JB-2 방습재 교체',
        siteArea: '2층 접속반',
        vendor: 'PV 메이트',
        scheduledAt: '2026-05-31 09:30',
        status: '예정',
        cost: '18만원',
        priority: '낮음',
        assignee: '시설관리팀 윤하늘',
        evidence: '습도 센서 트렌드와 점검 사진 첨부',
        decision: '정기 방문 일정에 묶어 처리',
      },
      {
        id: 202,
        title: '분기 열화상 촬영',
        siteArea: '전체 지붕',
        vendor: '드론솔라',
        scheduledAt: '2026-05-25 08:30',
        status: '완료',
        cost: '72만원',
        priority: '보통',
        assignee: '운영총괄 최유진',
        evidence: '열화상 이미지 42건, 핫스팟 없음',
        decision: '이상 없음으로 최종 확인 대기',
      },
    ],
  },
];

function StatCard({
  label,
  value,
  detail,
  trend,
}: {
  label: string;
  value: string;
  detail: string;
  trend: string;
}) {
  return (
    <div className="rounded border border-gray-800 bg-gray-900 p-4">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
      <div className="mt-2 flex items-center justify-between gap-3 text-xs">
        <span className="text-gray-400">{detail}</span>
        <span className="rounded bg-emerald-400/10 px-2 py-1 font-medium text-emerald-300">{trend}</span>
      </div>
    </div>
  );
}

function SectionHeader({ title, caption }: { title: string; caption: string }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="text-base font-semibold text-white">{title}</h2>
        <p className="mt-1 text-sm text-gray-500">{caption}</p>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: ScheduleStatus }) {
  const className = {
    예정: 'border-sky-400/40 bg-sky-400/10 text-sky-200',
    승인: 'border-yellow-400/40 bg-yellow-400/10 text-yellow-200',
    완료: 'border-emerald-400/40 bg-emerald-400/10 text-emerald-200',
    확인: 'border-gray-500 bg-gray-800 text-gray-200',
  }[status];

  return <span className={`rounded border px-2 py-1 text-xs font-medium ${className}`}>{status}</span>;
}

function nextStatus(status: ScheduleStatus) {
  const index = statusOrder.indexOf(status);
  return statusOrder[Math.min(index + 1, statusOrder.length - 1)];
}

function priorityClass(priority: MaintenanceTask['priority']) {
  return {
    높음: 'text-red-200',
    보통: 'text-yellow-200',
    낮음: 'text-gray-300',
  }[priority];
}

export default function SolarDashboardPage() {
  const [tasksByPlant, setTasksByPlant] = useState<Record<string, MaintenanceTask[]>>(() =>
    Object.fromEntries(plantDashboards.map((plant) => [plant.name, plant.tasks]))
  );
  const [activePlant, setActivePlant] = useState(plantDashboards[0].name);
  const activeData = plantDashboards.find((plant) => plant.name === activePlant) ?? plantDashboards[0];
  const tasks = tasksByPlant[activeData.name] ?? activeData.tasks;
  const [selectedTaskIdByPlant, setSelectedTaskIdByPlant] = useState<Record<string, number>>(() =>
    Object.fromEntries(plantDashboards.map((plant) => [plant.name, plant.tasks[0]?.id ?? 0]))
  );
  const selectedTaskId = selectedTaskIdByPlant[activeData.name] ?? tasks[0]?.id;
  const selectedTask = tasks.find((task) => task.id === selectedTaskId) ?? tasks[0];

  const statusCounts = statusOrder.map((status) => ({
    status,
    count: tasks.filter((task) => task.status === status).length,
  }));

  function advanceTask(id: number) {
    setTasksByPlant((current) => ({
      ...current,
      [activeData.name]: (current[activeData.name] ?? activeData.tasks).map((task) =>
        task.id === id ? { ...task, status: nextStatus(task.status) } : task
      ),
    }));
  }

  function selectPlant(name: string) {
    setActivePlant(name);
  }

  return (
    <main className="min-h-0 flex-1 bg-gray-950 text-white">
      <div className="flex h-full min-h-0 flex-col lg:flex-row">
        <aside className="shrink-0 border-b border-gray-800 bg-gray-950 lg:h-full lg:w-72 lg:border-b-0 lg:border-r">
          <div className="flex h-full min-h-0 flex-col">
            <div className="border-b border-gray-800 p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-yellow-300">Portfolio</p>
              <div className="mt-3 space-y-2">
                {plantDashboards.map((plant) => (
                  <button
                    key={plant.name}
                    onClick={() => selectPlant(plant.name)}
                    className={`w-full rounded border p-3 text-left transition-colors ${
                      activePlant === plant.name
                        ? 'border-yellow-400 bg-yellow-400/10'
                        : 'border-gray-800 bg-gray-900 hover:bg-gray-800'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-medium text-white">{plant.name}</span>
                      <span className={plant.state === '정상' ? 'text-xs text-emerald-300' : 'text-xs text-yellow-200'}>
                        {plant.state}
                      </span>
                    </div>
                    <div className="mt-2 flex justify-between text-xs text-gray-500">
                      <span>{plant.capacity}</span>
                      <span>{plant.output}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <nav className="border-b border-gray-800 p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Dashboard Areas</p>
              <div className="mt-3 space-y-1">
                {sidebarSections.map((section) => (
                  <a
                    key={section.label}
                    href={`#${section.label.replace('/', '-')}`}
                    className="flex items-center justify-between rounded px-3 py-2 text-sm text-gray-300 hover:bg-gray-900 hover:text-white"
                  >
                    <span>{section.label}</span>
                    <span className="rounded bg-gray-800 px-2 py-0.5 text-[11px] text-gray-400">{section.count}</span>
                  </a>
                ))}
              </div>
            </nav>

            <div className="min-h-0 flex-1 overflow-y-auto p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Critical Alerts</p>
              <div className="mt-3 space-y-3">
                {activeData.anomalyRows.slice(0, 2).map((row) => (
                  <div key={row.target} className="rounded border border-gray-800 bg-gray-900 p-3">
                    <div className="flex justify-between gap-2">
                      <span className="text-sm font-medium text-white">{row.target}</span>
                      <span className={row.severity === '높음' ? 'text-xs text-red-300' : 'text-xs text-yellow-200'}>
                        {row.severity}
                      </span>
                    </div>
                    <p className="mt-2 text-xs leading-5 text-gray-500">{row.action}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </aside>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto flex max-w-[1560px] flex-col gap-5 p-5">
            <section id="운영 개요" className="grid gap-4 xl:grid-cols-[1.35fr_0.9fr]">
              <div className="rounded border border-gray-800 bg-gray-900 p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-yellow-300">Plant Command Center</p>
                    <h1 className="mt-2 text-2xl font-semibold">{activeData.name} 태양광 발전소</h1>
                    <p className="mt-2 text-sm text-gray-400">
                      {activeData.capacity} · {activeData.connection} · 마지막 데이터 수신 {activeData.lastSeen}
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-right text-xs sm:grid-cols-4">
                    {statusCounts.map((item) => (
                      <div key={item.status} className="rounded border border-gray-800 bg-gray-950 px-3 py-2">
                        <div className="text-gray-500">{item.status}</div>
                        <div className="mt-1 text-lg font-semibold text-white">{item.count}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  {activeData.statCards.map((card) => (
                    <StatCard key={card.label} {...card} />
                  ))}
                </div>

                <div className="mt-5 grid gap-3 md:grid-cols-3">
                  {activeData.secondaryMetrics.map(([label, value, detail]) => (
                    <div key={label} className="rounded border border-gray-800 bg-gray-950 p-3">
                      <div className="text-xs text-gray-500">{label}</div>
                      <div className="mt-1 text-lg font-semibold text-white">{value}</div>
                      <div className="mt-1 text-xs text-gray-500">{detail}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div id="이상 탐지" className="rounded border border-red-500/30 bg-red-500/10 p-5">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-red-200">Anomaly Detection</p>
                    <h2 className="mt-2 text-xl font-semibold text-white">주의 필요 설비 {activeData.anomalyRows.length}건</h2>
                  </div>
                  <span className="rounded bg-red-400 px-3 py-1 text-sm font-semibold text-gray-950">위험 {activeData.risk}</span>
                </div>
                <div className="mt-4 space-y-3 text-sm">
                  {activeData.anomalyRows.map((row) => (
                    <div key={row.target} className="rounded border border-gray-800 bg-gray-950/70 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="font-medium text-white">{row.target}</div>
                        <div className={row.severity === '높음' ? 'text-xs text-red-300' : 'text-xs text-yellow-200'}>
                          {row.severity}
                        </div>
                      </div>
                      <div className="mt-2 text-gray-400">{row.cause}</div>
                      <div className="mt-1 text-xs text-gray-500">{row.evidence}</div>
                      <div className="mt-2 rounded bg-gray-900 px-2 py-1 text-xs text-gray-300">{row.action}</div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section id="정밀 모니터링" className="grid gap-4 xl:grid-cols-[1fr_0.9fr_0.9fr]">
              <div className="rounded border border-gray-800 bg-gray-900 p-5">
                <SectionHeader title="시간대별 발전량" caption="예측값, 실측값, 기상 조건을 함께 확인합니다." />
                <div className="mt-5 flex h-56 items-end gap-2">
                  {activeData.hourlyGeneration.map((value, index) => (
                    <div key={index} className="flex min-w-0 flex-1 flex-col items-center gap-2">
                      <div className="relative flex w-full items-end rounded-t bg-gray-800" style={{ height: '180px' }}>
                        <div className="w-full rounded-t bg-yellow-300" style={{ height: `${value * 1.45}px` }} />
                        <div className="absolute left-0 right-0 top-7 border-t border-dashed border-sky-400/60" />
                      </div>
                      <span className="text-[10px] text-gray-500">{index + 7}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
                  {activeData.generationSummary.map((summary) => (
                    <div key={summary} className="rounded bg-gray-950 p-2 text-gray-400">{summary}</div>
                  ))}
                </div>
              </div>

              <div className="rounded border border-gray-800 bg-gray-900 p-5">
                <SectionHeader title="인버터 상세" caption="효율, 온도, 출력 편차를 장비별로 봅니다." />
                <div className="mt-4 overflow-hidden rounded border border-gray-800">
                  <div className="grid grid-cols-[0.8fr_0.8fr_0.8fr_0.7fr_0.7fr] bg-gray-950 px-3 py-2 text-xs text-gray-500">
                    <span>장비</span>
                    <span>출력</span>
                    <span>효율</span>
                    <span>온도</span>
                    <span>상태</span>
                  </div>
                  {activeData.inverterRows.map((row) => (
                    <div key={row.name} className="grid grid-cols-[0.8fr_0.8fr_0.8fr_0.7fr_0.7fr] border-t border-gray-800 px-3 py-3 text-sm">
                      <span className="text-gray-200">{row.name}</span>
                      <span className="text-gray-400">{row.output}</span>
                      <span className="text-gray-400">{row.efficiency}</span>
                      <span className={row.status === '주의' ? 'text-yellow-200' : 'text-gray-400'}>{row.temp}</span>
                      <span className={row.status === '주의' ? 'text-yellow-200' : 'text-emerald-300'}>{row.status}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded border border-gray-800 bg-gray-900 p-5">
                <SectionHeader title="스트링 성능 비교" caption="동일 방위/경사 조건 기준의 상대 성능입니다." />
                <div className="mt-4 space-y-3">
                  {activeData.stringPerformance.map((item) => (
                    <div key={item.name} className="grid grid-cols-[44px_1fr_54px_44px] items-center gap-3 text-sm">
                      <span className="text-gray-400">{item.name}</span>
                      <div className="h-2 rounded bg-gray-800">
                        <div className={`h-2 rounded ${item.tone}`} style={{ width: `${item.value}%` }} />
                      </div>
                      <span className="text-right font-medium text-gray-100">{item.value}%</span>
                      <span className="text-right text-xs text-gray-500">{item.loss}</span>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
              <div className="rounded border border-gray-800 bg-gray-900 p-5">
                <SectionHeader title="기상 영향 분석" caption="발전량 편차를 일사량, 온도, 풍속, 구름량으로 분해합니다." />
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {activeData.weatherImpact.map((item) => (
                    <div key={item.label} className="rounded border border-gray-800 bg-gray-950 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm text-gray-400">{item.label}</span>
                        <span className={item.delta.startsWith('+') ? 'text-sm text-emerald-300' : 'text-sm text-red-300'}>
                          {item.delta}
                        </span>
                      </div>
                      <div className="mt-2 text-xl font-semibold text-white">{item.value}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded border border-gray-800 bg-gray-900 p-5">
                <SectionHeader title="성능 저하 추세" caption="최근 90일 PR, 오염, 열화, 차단 손실을 나누어 봅니다." />
                <div className="mt-5 grid gap-4 md:grid-cols-4">
                  {activeData.degradation.map(([label, value, detail]) => (
                    <div key={label} className="rounded border border-gray-800 bg-gray-950 p-4">
                      <div className="text-xs text-gray-500">{label}</div>
                      <div className="mt-2 text-xl font-semibold text-white">{value}</div>
                      <div className="mt-1 text-xs text-gray-500">{detail}</div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section id="관리 일정" className="grid gap-4 xl:grid-cols-[1fr_0.85fr]">
              <div className="rounded border border-gray-800 bg-gray-900">
                <div className="border-b border-gray-800 p-5">
                  <SectionHeader title="관리 일정" caption="업체 선정, 승인, 완료 인증, 최종 의뢰 확인 흐름을 한 화면에서 관리합니다." />
                </div>
                <div className="divide-y divide-gray-800">
                  {tasks.map((task) => (
                    <button
                      key={task.id}
                      onClick={() => setSelectedTaskIdByPlant((current) => ({ ...current, [activeData.name]: task.id }))}
                      className={`grid w-full gap-3 p-4 text-left transition-colors xl:grid-cols-[1fr_110px_88px_120px] ${
                        selectedTaskId === task.id ? 'bg-gray-800/70' : 'hover:bg-gray-800/40'
                      }`}
                    >
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-medium text-white">{task.title}</span>
                          <StatusBadge status={task.status} />
                        </div>
                        <div className="mt-1 text-sm text-gray-500">{task.siteArea} · {task.vendor} · {task.scheduledAt}</div>
                      </div>
                      <div className={`text-sm ${priorityClass(task.priority)}`}>{task.priority}</div>
                      <div className="text-sm text-gray-300">{task.cost}</div>
                      <div className="text-sm text-gray-400">{task.assignee.split(' ')[0]}</div>
                    </button>
                  ))}
                </div>
              </div>

              <aside className="rounded border border-gray-800 bg-gray-900 p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-base font-semibold">{selectedTask.title}</h2>
                    <p className="mt-1 text-sm text-gray-500">{selectedTask.vendor} · {selectedTask.cost}</p>
                  </div>
                  <StatusBadge status={selectedTask.status} />
                </div>

                <div className="mt-5 grid grid-cols-4 gap-2">
                  {statusOrder.map((status, index) => {
                    const isActive = statusOrder.indexOf(selectedTask.status) >= index;
                    return (
                      <div key={status} className="min-w-0">
                        <div className={`h-2 rounded ${isActive ? 'bg-yellow-300' : 'bg-gray-800'}`} />
                        <div className={`mt-2 text-center text-xs ${isActive ? 'text-yellow-100' : 'text-gray-600'}`}>{status}</div>
                      </div>
                    );
                  })}
                </div>

                <dl className="mt-6 space-y-3 text-sm">
                  <div className="flex justify-between gap-4 border-b border-gray-800 pb-3">
                    <dt className="text-gray-500">대상 설비</dt>
                    <dd className="text-right text-gray-100">{selectedTask.siteArea}</dd>
                  </div>
                  <div className="flex justify-between gap-4 border-b border-gray-800 pb-3">
                    <dt className="text-gray-500">작업 일정</dt>
                    <dd className="text-right text-gray-100">{selectedTask.scheduledAt}</dd>
                  </div>
                  <div className="flex justify-between gap-4 border-b border-gray-800 pb-3">
                    <dt className="text-gray-500">담당자</dt>
                    <dd className="text-right text-gray-100">{selectedTask.assignee}</dd>
                  </div>
                  <div className="border-b border-gray-800 pb-3">
                    <dt className="text-gray-500">선정/승인 근거</dt>
                    <dd className="mt-1 text-gray-100">{selectedTask.decision}</dd>
                  </div>
                  <div className="border-b border-gray-800 pb-3">
                    <dt className="text-gray-500">완료 인증 자료</dt>
                    <dd className="mt-1 text-gray-100">{selectedTask.evidence}</dd>
                  </div>
                </dl>

                <div className="mt-5 rounded border border-gray-800 bg-gray-950 p-4">
                  <div className="text-sm font-medium text-white">업체 제출 자료</div>
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    <div className="grid h-16 place-items-center rounded bg-gray-800 text-[11px] text-gray-500">사진</div>
                    <div className="grid h-16 place-items-center rounded bg-gray-800 text-[11px] text-gray-500">열화상</div>
                    <div className="grid h-16 place-items-center rounded bg-gray-800 text-[11px] text-gray-500">계측표</div>
                  </div>
                  <p className="mt-3 text-xs leading-5 text-gray-500">사진, 열화상 이미지, 계측표, 작업자 위치 기록을 묶어 검수자가 확인하는 영역입니다.</p>
                </div>

                <button
                  onClick={() => advanceTask(selectedTask.id)}
                  disabled={selectedTask.status === '확인'}
                  className="mt-5 w-full rounded bg-yellow-400 px-4 py-3 text-sm font-semibold text-gray-950 transition-colors hover:bg-yellow-300 disabled:cursor-not-allowed disabled:bg-gray-800 disabled:text-gray-500"
                >
                  {selectedTask.status === '확인' ? '최종 확인 완료' : `${nextStatus(selectedTask.status)} 단계로 진행`}
                </button>
              </aside>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
