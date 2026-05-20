(function() {
  if (window.PulseHelp) return;

  const STYLES = `
    .pulse-help-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      animation: pulseHelpFadeIn 0.2s ease;
    }
    .pulse-help-overlay.active { display: flex; }

    @keyframes pulseHelpFadeIn {
      from { opacity: 0; }
      to   { opacity: 1; }
    }
    @keyframes pulseHelpSlideUp {
      from { opacity: 0; transform: translateY(20px) scale(0.98); }
      to   { opacity: 1; transform: translateY(0) scale(1); }
    }

    .pulse-help-modal {
      background: #0c0e13;
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 18px;
      width: 90%;
      max-width: 720px;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      animation: pulseHelpSlideUp 0.25s ease;
      box-shadow: 0 20px 60px rgba(0,0,0,0.5);
      font-family: 'Inter', sans-serif;
    }

    .pulse-help-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 22px 28px 18px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .pulse-help-title {
      font-size: 1.15rem;
      font-weight: 700;
      color: #f5f7fc;
      letter-spacing: -0.022em;
      margin: 0;
    }
    .pulse-help-subtitle {
      font-size: 0.78rem;
      color: #8b95ad;
      margin-top: 3px;
    }
    .pulse-help-close {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.08);
      color: #8b95ad;
      cursor: pointer;
      display: grid;
      place-items: center;
      font-size: 18px;
      font-family: 'Inter', sans-serif;
      transition: all 0.15s;
      line-height: 1;
    }
    .pulse-help-close:hover {
      background: rgba(255,76,110,0.1);
      color: #ff4c6e;
      border-color: rgba(255,76,110,0.25);
    }

    .pulse-help-tabs {
      display: flex;
      gap: 6px;
      padding: 14px 28px 0;
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .pulse-help-tab {
      background: none;
      border: none;
      color: #8b95ad;
      font-family: 'Inter', sans-serif;
      font-size: 0.85rem;
      font-weight: 500;
      padding: 10px 18px;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.18s;
      letter-spacing: -0.01em;
    }
    .pulse-help-tab:hover { color: #f5f7fc; }
    .pulse-help-tab.active {
      color: #00d4ff;
      border-bottom-color: #00d4ff;
    }

    .pulse-help-body {
      flex: 1;
      overflow-y: auto;
      padding: 24px 28px 28px;
      scrollbar-width: thin;
      scrollbar-color: rgba(255,255,255,0.1) transparent;
    }
    .pulse-help-body::-webkit-scrollbar { width: 6px; }
    .pulse-help-body::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }

    .pulse-help-section {
      display: none;
    }
    .pulse-help-section.active {
      display: block;
    }

    .pulse-help-section h3 {
      font-size: 0.95rem;
      font-weight: 700;
      color: #f5f7fc;
      margin: 24px 0 10px;
      letter-spacing: -0.018em;
    }
    .pulse-help-section h3:first-child { margin-top: 0; }

    .pulse-help-section p {
      font-size: 0.88rem;
      color: #8b95ad;
      line-height: 1.65;
      margin-bottom: 12px;
      letter-spacing: -0.005em;
    }

    .pulse-help-section strong {
      color: #f5f7fc;
      font-weight: 600;
    }

    .pulse-help-steps {
      list-style: none;
      padding: 0;
      margin: 14px 0;
      counter-reset: helpsteps;
    }
    .pulse-help-steps li {
      display: flex;
      align-items: flex-start;
      gap: 14px;
      padding: 12px 14px;
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.05);
      border-radius: 10px;
      margin-bottom: 8px;
      font-size: 0.86rem;
      color: #8b95ad;
      line-height: 1.55;
      counter-increment: helpsteps;
    }
    .pulse-help-steps li::before {
      content: counter(helpsteps);
      flex-shrink: 0;
      width: 24px;
      height: 24px;
      border-radius: 7px;
      background: linear-gradient(135deg, #00d4ff, #0099cc);
      color: #000;
      font-family: 'JetBrains Mono', monospace;
      font-weight: 700;
      font-size: 0.75rem;
      display: grid;
      place-items: center;
      margin-top: 1px;
    }
    .pulse-help-steps li b {
      color: #f5f7fc;
      font-weight: 600;
      display: block;
      margin-bottom: 2px;
      font-size: 0.88rem;
    }

    .pulse-help-cards {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 10px;
      margin: 12px 0;
    }
    .pulse-help-cards-2 {
      grid-template-columns: 1fr 1fr;
    }
    .pulse-help-card {
      padding: 14px 16px;
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 10px;
    }
    .pulse-help-card.acil { border-color: rgba(255,76,110,0.25); }
    .pulse-help-card.proaktif { border-color: rgba(255,186,48,0.25); }
    .pulse-help-card.sadakat { border-color: rgba(0,232,158,0.25); }

    .pulse-help-card-title {
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      margin-bottom: 5px;
    }
    .pulse-help-card.acil .pulse-help-card-title { color: #ff4c6e; }
    .pulse-help-card.proaktif .pulse-help-card-title { color: #ffba30; }
    .pulse-help-card.sadakat .pulse-help-card-title { color: #00e89e; }

    .pulse-help-card-desc {
      font-size: 0.78rem;
      color: #8b95ad;
      line-height: 1.5;
    }

    .pulse-help-tip {
      padding: 12px 16px;
      background: rgba(0,212,255,0.06);
      border: 1px solid rgba(0,212,255,0.18);
      border-radius: 10px;
      margin: 14px 0;
      font-size: 0.83rem;
      color: #f5f7fc;
      line-height: 1.6;
    }
    .pulse-help-tip-label {
      display: inline-block;
      font-weight: 700;
      color: #00d4ff;
      font-size: 0.72rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 4px;
    }

    .pulse-help-trigger-btn {
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.1);
      color: #8b95ad;
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 0.74rem;
      font-family: 'Inter', sans-serif;
      cursor: pointer;
      transition: all 0.18s;
      font-weight: 500;
    }
    .pulse-help-trigger-btn:hover {
      border-color: #00d4ff;
      color: #00d4ff;
      background: rgba(0,212,255,0.06);
    }
  `;

  const HTML = `
    <div class="pulse-help-overlay" id="pulseHelpOverlay">
      <div class="pulse-help-modal" onclick="event.stopPropagation()">
        <div class="pulse-help-header">
          <div>
            <h2 class="pulse-help-title">Pulse AI Kullanım Rehberi</h2>
            <p class="pulse-help-subtitle">Sistemin nasıl çalıştığını öğrenin</p>
          </div>
          <button class="pulse-help-close" onclick="PulseHelp.close()">×</button>
        </div>
        <div class="pulse-help-tabs">
          <button class="pulse-help-tab active" data-tab="genel">Genel</button>
          <button class="pulse-help-tab" data-tab="temsilci">Temsilci</button>
          <button class="pulse-help-tab" data-tab="yonetici">Yönetici</button>
        </div>
        <div class="pulse-help-body">

          <div class="pulse-help-section active" data-section="genel">
            <h3>Pulse AI Nedir?</h3>
            <p>Pulse AI, telekom sektörü için geliştirilmiş bir <strong>müşteri kayıp önleme karar destek sistemidir</strong>. CatBoost makine öğrenimi modeli ile müşterilerin terk etme olasılığını tahmin eder, SHAP ile bu tahminin nedenini açıklar ve Gemini AI ile uygulanabilir aksiyon önerileri sunar.</p>

            <h3>Sistemin Üç Katmanı</h3>
            <ol class="pulse-help-steps">
              <li><b>Tahmin Katmanı</b>Her müşteri için %0-100 arası bir kayıp olasılığı hesaplar. Eşik değeri %27.</li>
              <li><b>Açıklama Katmanı</b>SHAP analizi ile tahmini etkileyen en önemli 5 faktörü sayısal etkileriyle gösterir.</li>
              <li><b>Aksiyon Katmanı</b>Gemini AI risk faktörlerine göre teklif önerisi, çağrı senaryosu veya özet üretir.</li>
            </ol>

            <h3>Risk Segmentleri</h3>
            <p>Müşteriler kayıp olasılığına göre üç gruba ayrılır:</p>
            <div class="pulse-help-cards">
              <div class="pulse-help-card acil">
                <div class="pulse-help-card-title">Acil</div>
                <div class="pulse-help-card-desc">%50 ve üzeri. Hızlı retention aksiyonu gerekir.</div>
              </div>
              <div class="pulse-help-card proaktif">
                <div class="pulse-help-card-title">Proaktif</div>
                <div class="pulse-help-card-desc">%30 - %50. Önleyici temas önerilir.</div>
              </div>
              <div class="pulse-help-card sadakat">
                <div class="pulse-help-card-title">Sadakat</div>
                <div class="pulse-help-card-desc">%30 altı. Sadakat güçlendirme yeterli.</div>
              </div>
            </div>

            <div class="pulse-help-tip">
              <span class="pulse-help-tip-label">Bilgi</span><br>
              Sistem iki kullanıcı rolüyle çalışır: <strong>Temsilci</strong> ve <strong>Yönetici</strong>. Her rolün ayrı bir paneli vardır. Detaylı kullanım için diğer sekmelere bakın.
            </div>
          </div>

          <div class="pulse-help-section" data-section="temsilci">
            <h3>Temsilci Paneli Nedir?</h3>
            <p>Çağrı merkezi temsilcileri için tasarlanmış paneldir. Tek bir müşteriye odaklanır, AI destekli kayıp önleme önerileri sunar.</p>

            <h3>Adım Adım Kullanım</h3>
            <ol class="pulse-help-steps">
              <li><b>Müşteri ID girin</b>Arama kutusuna analiz etmek istediğiniz müşterinin ID'sini yazın ve "Analiz Et" tuşuna basın.</li>
              <li><b>Risk skorunu inceleyin</b>Sayfanın üstünde müşterinin kayıp olasılığı (%) ve risk seviyesi gösterilir.</li>
              <li><b>SHAP faktörlerini okuyun</b>Tahmini etkileyen 5 faktör listelenir. Kırmızı barlar riski artırır, yeşil barlar koruyucu etkidir.</li>
              <li><b>Müşteri verilerini gözden geçirin</b>Kullanım, çağrı kalitesi, retention geçmişi gibi metrikleri inceleyin.</li>
              <li><b>AI asistandan öneri alın</b>Sağdaki sohbet panelinde hızlı butonları veya serbest soru kullanın.</li>
            </ol>

            <h3>AI Asistan Hızlı Butonları</h3>
            <div class="pulse-help-cards pulse-help-cards-2">
              <div class="pulse-help-card">
                <div class="pulse-help-card-title" style="color:#00d4ff">Risk Faktörleri</div>
                <div class="pulse-help-card-desc">SHAP'tan gelen 3 önemli risk faktörünü detaylı açıklar.</div>
              </div>
              <div class="pulse-help-card">
                <div class="pulse-help-card-title" style="color:#00d4ff">Teklif Öner</div>
                <div class="pulse-help-card-desc">Müşteriye sunulacak somut bir teklif ve gerekçesini üretir.</div>
              </div>
              <div class="pulse-help-card">
                <div class="pulse-help-card-title" style="color:#00d4ff">Senaryo</div>
                <div class="pulse-help-card-desc">Müşteriyle yapılacak görüşme için diyalog formatında senaryo sunar.</div>
              </div>
              <div class="pulse-help-card">
                <div class="pulse-help-card-title" style="color:#00d4ff">Özet</div>
                <div class="pulse-help-card-desc">Müşterinin profilini ve davranışını yapılandırılmış özet halinde verir.</div>
              </div>
            </div>

            <div class="pulse-help-tip">
              <span class="pulse-help-tip-label">İpucu</span><br>
              Hızlı butonları kullanmak yerine kendi sorunuzu da yazabilirsiniz. Örneğin: "Bu müşteri için sadakat indirimi mantıklı mı?" gibi.
            </div>
          </div>

          <div class="pulse-help-section" data-section="yonetici">
            <h3>Yönetici Paneli Nedir?</h3>
            <p>Retention yöneticileri için tasarlanmış üst seviye paneldir. Müşteri portföyünün genel görünümünü sunar, segment bazlı listeler ve PDF rapor oluşturur.</p>

            <h3>Adım Adım Kullanım</h3>
            <ol class="pulse-help-steps">
              <li><b>Sayfa otomatik yüklenir</b>Giriş yaptığınızda sistem 100 müşteriyi analiz eder ve 3 segmente ayırır.</li>
              <li><b>Segment kartlarını inceleyin</b>Üstte Acil, Proaktif ve Sadakat segmentlerindeki müşteri sayıları gösterilir.</li>
              <li><b>Listelerden müşteri seçin</b>Her segmentteki en riskli 10 müşteri listelenir. Detay görmek için satıra tıklayın.</li>
              <li><b>Müşteri detayını inceleyin</b>Salt okunur modda müşterinin SHAP analizi ve verileri gösterilir. Geri tuşu ile listeye dönersiniz.</li>
              <li><b>PDF rapor indirin</b>Sağ üstteki "Raporu İndir" butonu tüm segmentleri içeren profesyonel bir PDF oluşturur.</li>
            </ol>

            <h3>PDF Raporda Neler Var?</h3>
            <ol class="pulse-help-steps">
              <li><b>Yönetici Özeti</b>Toplam müşteri sayısı, segment dağılımı, önerilen yaklaşımlar.</li>
              <li><b>Segment Dağılım Grafiği</b>Pasta ve bar grafikleri ile görsel özet.</li>
              <li><b>Üç Detaylı Tablo</b>Her segment için ID, meslek, hizmet süresi, gelir ve risk yüzdesi.</li>
              <li><b>Metodoloji</b>Model performansı, eşik değeri, veri kaynağı bilgileri.</li>
            </ol>

            <div class="pulse-help-tip">
              <span class="pulse-help-tip-label">Önemli</span><br>
              Yönetici panelinde AI sohbet özelliği bulunmaz. Bireysel müşteri için AI önerisi almak isterseniz Temsilci panelini kullanabilirsiniz.
            </div>
          </div>

        </div>
      </div>
    </div>
  `;

  function init() {
    const styleTag = document.createElement('style');
    styleTag.textContent = STYLES;
    document.head.appendChild(styleTag);

    const div = document.createElement('div');
    div.innerHTML = HTML;
    document.body.appendChild(div.firstElementChild);

    const overlay = document.getElementById('pulseHelpOverlay');
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) close();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') close();
    });

    document.querySelectorAll('.pulse-help-tab').forEach(tab => {
      tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });
  }

  function open() {
    document.getElementById('pulseHelpOverlay').classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    document.getElementById('pulseHelpOverlay').classList.remove('active');
    document.body.style.overflow = '';
  }

  function switchTab(name) {
    document.querySelectorAll('.pulse-help-tab').forEach(t => {
      t.classList.toggle('active', t.dataset.tab === name);
    });
    document.querySelectorAll('.pulse-help-section').forEach(s => {
      s.classList.toggle('active', s.dataset.section === name);
    });
    document.querySelector('.pulse-help-body').scrollTop = 0;
  }

  function injectButton(targetSelector, beforeSelector) {
    const target = document.querySelector(targetSelector);
    if (!target) return;
    const btn = document.createElement('button');
    btn.className = 'pulse-help-trigger-btn';
    btn.innerHTML = 'Yardım';
    btn.onclick = open;
    if (beforeSelector) {
      const ref = target.querySelector(beforeSelector);
      if (ref) target.insertBefore(btn, ref);
      else target.appendChild(btn);
    } else {
      target.appendChild(btn);
    }
  }

  window.PulseHelp = { open, close, switchTab, injectButton };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
