// P2-29. The WPF dashboard, moved out of RiskGuardAddOn.cs verbatim.
//
// That file was 7,058 lines -- the plan entry says 4,108, which is how stale a size claim gets
// while nothing measures it. ~720 of those lines were this window, which shares NOTHING with the
// guard but a namespace: it reads `_addOn`'s public surface and draws. It is not even compiled
// into the same builds, being wrapped in `#if !TESTING` end to end.
//
// ⚠️ THIS IS A MOVE, NOT A REWRITE. Every line below is byte-identical to what it replaced, and
// the commit that made it changed no behaviour: the suite was 1469/0 before and after, and
// `nt_compile` is what proves the half the suite CANNOT see, because the test build excludes
// exactly this file's contents. A refactor that "looks fine and compiles under TESTING" would
// have proved nothing about the code an operator actually runs.
//
// WHY THESE TYPES AND NOT A `partial class` SPLIT: RiskGuardWindow and CardControls are their own
// top-level types. Relocating them needs no `partial` keyword and cannot reshuffle a member, so
// there is no mechanism by which it could change what the guard does. The plan proposes splitting
// RiskGuardAddOn itself into seven partials as well; that is a larger change with a real failure
// mode, and it is deliberately not bundled in here.
//
// Nothing needed registering: tools/sync_nt8.py and tests/RiskGuardTests.csproj both already glob
// `addons/*.cs`. Had either been a hand-typed list, this file would have been invisible to it --
// the drift that bit `check_bridge_parses.py` and `BridgeTests.csproj` in the sibling repo.
#if !TESTING
using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Tools;
#endif

namespace NinjaTrader.NinjaScript.AddOns
{
    // -
    // WPF UI DASHBOARD
    // -

#if !TESTING
    public class RiskGuardWindow : Window
    {
        private readonly RiskGuardAddOn _addOn;
        private DispatcherTimer _uiTimer;
        private TextBlock _armedStatusText;
        private Button _toggleArmedBtn;
        private Button _panicAllBtn;
        private WrapPanel _cardsPanel;
        
        private readonly Dictionary<string, CardControls> _cardControls = new Dictionary<string, CardControls>();

        // Config UI fields
        private ComboBox _modeCombo;
        private CheckBox _windowGateCheck;
        private TextBox _maxContractsAccountText;
        private TextBox _maxContractsAggregateText;
        private TextBox _maxTradesSessionText;
        private TextBox _maxConsecutiveLossesText;
        private TextBox _cooldownMinutesText;
        private TextBox _lockoutMinutesText;
        private TextBox _dailyLossLimitText;
        private TextBox _trailingDrawdownText;
        private TextBox _pnlLockoutMinutesText;
        private ComboBox _onMissingCombo;
        private TextBox _stopAttachSecondsText;
        private TextBox _expectedCopiesText;
        private TextBox _excludedAccountsText;
        private CheckBox _firmMirrorEnabledCheck;
        private TextBox _firmTrailingDDAmountText;
        private TextBox _firmDailyLossAmountText;

        // Search and Filter fields
        private TextBox _searchBox;
        private CheckBox _hideInactiveCheck;

        // Track which accounts have already shown a lockout-stuck popup
        // so we don't spam the user every 500ms UI tick.
        private readonly HashSet<string> _lockoutStuckPopupShown = new HashSet<string>();

        public RiskGuardWindow(RiskGuardAddOn addOn)
        {
            _addOn = addOn;
            Title = $"NinjaTrader Cross-Account Risk Guard Dashboard v{RiskGuardAddOn.Version}";
            Width = 1000;
            Height = 700;
            Background = new SolidColorBrush(Color.FromRgb(30, 30, 30));
            WindowStartupLocation = WindowStartupLocation.CenterScreen;

            var mainGrid = new Grid();
            mainGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            mainGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });

            // TOP BAR (dark theme)
            var topBar = new Border { Background = new SolidColorBrush(Color.FromRgb(45, 45, 48)), Padding = new Thickness(10) };
            var topGrid = new Grid();
            topGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            topGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            topGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            topBar.Child = topGrid;

            var statusPanel = new StackPanel { Orientation = Orientation.Horizontal };
            statusPanel.Children.Add(new TextBlock { Text = "- RISK GUARD: ", Foreground = Brushes.White, FontSize = 14, FontWeight = FontWeights.Bold, VerticalAlignment = VerticalAlignment.Center });
            
            _armedStatusText = new TextBlock { FontSize = 14, FontWeight = FontWeights.Bold, VerticalAlignment = VerticalAlignment.Center };
            statusPanel.Children.Add(_armedStatusText);

            _toggleArmedBtn = new Button 
            { 
                Content = "TOGGLE ARMED", 
                Margin = new Thickness(15, 0, 0, 0),
                Padding = new Thickness(10, 3, 10, 3),
                Background = new SolidColorBrush(Color.FromRgb(63, 63, 70)),
                Foreground = Brushes.White,
                BorderBrush = Brushes.Transparent
            };
            _toggleArmedBtn.Click += OnToggleArmedClick;
            statusPanel.Children.Add(_toggleArmedBtn);
            
            var reloadBtn = new Button 
            { 
                Content = "RELOAD CONFIG", 
                Margin = new Thickness(10, 0, 0, 0),
                Padding = new Thickness(10, 3, 10, 3),
                Background = new SolidColorBrush(Color.FromRgb(63, 63, 70)),
                Foreground = Brushes.White,
                BorderBrush = Brushes.Transparent
            };
            reloadBtn.Click += OnReloadConfigClick;
            statusPanel.Children.Add(reloadBtn);

            // Add Search Box
            statusPanel.Children.Add(new TextBlock { Text = "Filter:", Foreground = Brushes.LightGray, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(20, 0, 5, 0) });
            _searchBox = new TextBox { Width = 90, Height = 22, VerticalAlignment = VerticalAlignment.Center, Background = new SolidColorBrush(Color.FromRgb(40, 40, 40)), Foreground = Brushes.White, BorderBrush = new SolidColorBrush(Color.FromRgb(63, 63, 70)) };
            statusPanel.Children.Add(_searchBox);

            // Add Hide Inactive Checkbox
            _hideInactiveCheck = new CheckBox { Content = "Hide Inactive ($0 Bal)", IsChecked = true, Foreground = Brushes.LightGray, Margin = new Thickness(15, 0, 0, 0), VerticalAlignment = VerticalAlignment.Center };
            statusPanel.Children.Add(_hideInactiveCheck);

            Grid.SetColumn(statusPanel, 0);
            topGrid.Children.Add(statusPanel);

            _panicAllBtn = new Button
            {
                Content = "- PANIC FLATTEN ALL ACCOUNTS",
                FontWeight = FontWeights.Bold,
                Background = new SolidColorBrush(Color.FromRgb(180, 40, 40)),
                Foreground = Brushes.White,
                Padding = new Thickness(15, 5, 15, 5),
                BorderBrush = Brushes.Transparent
            };
            _panicAllBtn.Click += OnPanicAllClick;
            Grid.SetColumn(_panicAllBtn, 2);
            topGrid.Children.Add(_panicAllBtn);

            Grid.SetRow(topBar, 0);
            mainGrid.Children.Add(topBar);

            // TABS CONTROL
            var tabControl = new TabControl 
            { 
                Background = new SolidColorBrush(Color.FromRgb(30, 30, 30)),
                BorderBrush = new SolidColorBrush(Color.FromRgb(45, 45, 48)),
                Margin = new Thickness(5)
            };

            // TAB 1: ACCOUNTS OVERVIEW
            var accountsTab = new TabItem 
            { 
                Header = "Accounts Overview",
                Background = new SolidColorBrush(Color.FromRgb(45, 45, 48)),
                Foreground = Brushes.White
            };
            var scrollViewer = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
            _cardsPanel = new WrapPanel { ItemWidth = 220, ItemHeight = 200 };
            scrollViewer.Content = _cardsPanel;
            accountsTab.Content = scrollViewer;
            tabControl.Items.Add(accountsTab);

            // TAB 2: CONFIGURATION EDITOR
            var configTab = new TabItem 
            { 
                Header = "Risk & Settings Configuration",
                Background = new SolidColorBrush(Color.FromRgb(45, 45, 48)),
                Foreground = Brushes.White
            };
            
            var editorScroll = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
            var border = new Border { Padding = new Thickness(20), Background = new SolidColorBrush(Color.FromRgb(35, 35, 35)) };
            var panel = new StackPanel();
            border.Child = panel;
            editorScroll.Content = border;

            panel.Children.Add(new TextBlock { Text = "Global Protection Settings", FontSize = 16, FontWeight = FontWeights.Bold, Foreground = Brushes.White, Margin = new Thickness(0, 0, 0, 15) });

            // Helper to add editable text row
            Func<string, string, TextBox, StackPanel> addEditRow = (label, tooltip, box) =>
            {
                var row = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 5, 0, 5) };
                row.Children.Add(new TextBlock { Text = label, Width = 220, Foreground = Brushes.LightGray, VerticalAlignment = VerticalAlignment.Center });
                box.Width = 100;
                box.Height = 22;
                box.Background = new SolidColorBrush(Color.FromRgb(45, 45, 45));
                box.Foreground = Brushes.White;
                box.BorderBrush = new SolidColorBrush(Color.FromRgb(65, 65, 65));
                row.Children.Add(box);
                row.Children.Add(new TextBlock { Text = tooltip, Foreground = Brushes.Gray, Margin = new Thickness(10, 0, 0, 0), VerticalAlignment = VerticalAlignment.Center, FontSize = 11 });
                return row;
            };

            // Mode Combo
            var modeRow = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 5, 0, 5) };
            modeRow.Children.Add(new TextBlock { Text = "Operational Mode:", Width = 220, Foreground = Brushes.LightGray, VerticalAlignment = VerticalAlignment.Center });
            _modeCombo = new ComboBox { Width = 100, Height = 22, Background = new SolidColorBrush(Color.FromRgb(45, 45, 45)), Foreground = Brushes.White };
            _modeCombo.Items.Add("shadow");
            _modeCombo.Items.Add("live");
            modeRow.Children.Add(_modeCombo);
            panel.Children.Add(modeRow);

            // WindowGate Checkbox
            var gateRow = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 5, 0, 5) };
            gateRow.Children.Add(new TextBlock { Text = "Restrict Outside Trading Hours:", Width = 220, Foreground = Brushes.LightGray, VerticalAlignment = VerticalAlignment.Center });
            _windowGateCheck = new CheckBox { VerticalAlignment = VerticalAlignment.Center };
            gateRow.Children.Add(_windowGateCheck);
            panel.Children.Add(gateRow);

            // Populate all fields
            _maxContractsAccountText = new TextBox();
            panel.Children.Add(addEditRow("Max Contracts Per Account:", "Max size in standard contracts per single account", _maxContractsAccountText));

            _maxContractsAggregateText = new TextBox();
            panel.Children.Add(addEditRow("Max Contracts Aggregate:", "Combined max size across all copy group accounts", _maxContractsAggregateText));

            _maxTradesSessionText = new TextBox();
            panel.Children.Add(addEditRow("Max Trades Per Session:", "Prevents overtrading after N executions", _maxTradesSessionText));

            _maxConsecutiveLossesText = new TextBox();
            panel.Children.Add(addEditRow("Max Consecutive Losses:", "Locks out account if N losses occur in a row", _maxConsecutiveLossesText));

            _cooldownMinutesText = new TextBox();
            panel.Children.Add(addEditRow("Cooldown Period (Mins):", "Cooldown duration after a consecutive loss lockout", _cooldownMinutesText));

            _lockoutMinutesText = new TextBox();
            panel.Children.Add(addEditRow("Lockout Duration (Mins):", "Duration for time-based rule lockouts (0 = lock rest of day)", _lockoutMinutesText));

            _dailyLossLimitText = new TextBox();
            panel.Children.Add(addEditRow("Daily Loss Limit ($):", "Hard daily drawdown limit per account", _dailyLossLimitText));

            _trailingDrawdownText = new TextBox();
            panel.Children.Add(addEditRow("Trailing Drawdown ($):", "Max allowable drawdown from peak session equity", _trailingDrawdownText));

            _pnlLockoutMinutesText = new TextBox();
            panel.Children.Add(addEditRow("PnL Lockout (Mins):", "Lockout duration after hitting Daily Loss / Trailing Drawdown", _pnlLockoutMinutesText));

            // OnMissing Combo
            var missingRow = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 5, 0, 5) };
            missingRow.Children.Add(new TextBlock { Text = "On Missing Bracket Order:", Width = 220, Foreground = Brushes.LightGray, VerticalAlignment = VerticalAlignment.Center });
            _onMissingCombo = new ComboBox { Width = 100, Height = 22, Background = new SolidColorBrush(Color.FromRgb(45, 45, 45)), Foreground = Brushes.White };
            _onMissingCombo.Items.Add("AutoStop");
            _onMissingCombo.Items.Add("Flatten");
            missingRow.Children.Add(_onMissingCombo);
            panel.Children.Add(missingRow);

            // StopGuard grace period
            _stopAttachSecondsText = new TextBox();
            panel.Children.Add(addEditRow("Stop Attach Grace (Sec):", "Grace period before auto-stop/flatten on missing bracket", _stopAttachSecondsText));

            // Expected copies (N-way mirror)
            _expectedCopiesText = new TextBox();
            panel.Children.Add(addEditRow("Expected Copies (Mirror N):", "Intended N-way mirror count (1 = no mirroring)", _expectedCopiesText));

            // Excluded accounts (global text editor)
            _excludedAccountsText = new TextBox();
            _excludedAccountsText.Width = 300;
            _excludedAccountsText.Height = 22;
            panel.Children.Add(addEditRow("Excluded Accounts (comma-sep):", "Accounts excluded from all rules (also toggle per-card)", _excludedAccountsText));

            // Firm Mirror section header
            panel.Children.Add(new TextBlock { Text = "Firm Mirror (Prop-Firm Rule Replication)", FontSize = 14, FontWeight = FontWeights.Bold, Foreground = Brushes.LightGray, Margin = new Thickness(0, 15, 0, 5) });

            // FirmMirror Enabled checkbox
            var firmRow = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 5, 0, 5) };
            firmRow.Children.Add(new TextBlock { Text = "Firm Mirror Enabled:", Width = 220, Foreground = Brushes.LightGray, VerticalAlignment = VerticalAlignment.Center });
            _firmMirrorEnabledCheck = new CheckBox { VerticalAlignment = VerticalAlignment.Center };
            firmRow.Children.Add(_firmMirrorEnabledCheck);
            panel.Children.Add(firmRow);

            _firmTrailingDDAmountText = new TextBox();
            panel.Children.Add(addEditRow("Firm Trailing DD ($):", "Prop-firm trailing drawdown limit (with buffer)", _firmTrailingDDAmountText));

            _firmDailyLossAmountText = new TextBox();
            panel.Children.Add(addEditRow("Firm Daily Loss ($):", "Prop-firm daily loss limit (with buffer)", _firmDailyLossAmountText));

            // SAVE CONFIG BUTTON
            var saveBtn = new Button
            {
                Content = "- SAVE AND APPLY CONFIGURATION",
                Width = 250,
                Height = 35,
                Margin = new Thickness(0, 20, 0, 0),
                HorizontalAlignment = HorizontalAlignment.Left,
                FontWeight = FontWeights.Bold,
                Background = new SolidColorBrush(Color.FromRgb(0, 122, 204)),
                Foreground = Brushes.White,
                BorderBrush = Brushes.Transparent
            };
            saveBtn.Click += OnSaveConfigClick;
            panel.Children.Add(saveBtn);

            configTab.Content = editorScroll;
            tabControl.Items.Add(configTab);

            // TAB 3: TRADE COPIER & GROUP MANAGER
            var copierTab = new TabItem
            {
                Header = "Trade Copier & Group Manager",
                Background = new SolidColorBrush(Color.FromRgb(45, 45, 48)),
                Foreground = Brushes.White
            };
            copierTab.Content = new TradeCopierControl();
            tabControl.Items.Add(copierTab);

            Grid.SetRow(tabControl, 1);
            mainGrid.Children.Add(tabControl);

            Content = mainGrid;

            // Load initial config values
            LoadConfigIntoUI();

            // Timer to refresh UI stats
            _uiTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(500) };
            _uiTimer.Tick += (s, e) => UpdateUI();
            _uiTimer.Start();

            Closed += (s, e) => _uiTimer.Stop();

            UpdateUI();
        }

        private void LoadConfigIntoUI()
        {
            var cfg = _addOn.Config;
            if (cfg == null) return;

            _modeCombo.SelectedItem = cfg.Mode == "live" ? "live" : "shadow";
            _windowGateCheck.IsChecked = cfg.EnableWindowGate;
            _maxContractsAccountText.Text = cfg.Sizing.MaxContractsPerAccount.ToString();
            _maxContractsAggregateText.Text = cfg.Sizing.MaxContractsAggregate.ToString();
            _maxTradesSessionText.Text = cfg.Overtrading.MaxTradesPerSession.ToString();
            _maxConsecutiveLossesText.Text = cfg.Overtrading.MaxConsecutiveLosses.ToString();
            _cooldownMinutesText.Text = cfg.Overtrading.CooldownMinutes.ToString();
            _lockoutMinutesText.Text = cfg.Overtrading.LockoutMinutes.ToString();
            _dailyLossLimitText.Text = cfg.PnLRules.DailyLossLimit.ToString();
            _trailingDrawdownText.Text = cfg.PnLRules.TrailingDrawdown.ToString();
            _pnlLockoutMinutesText.Text = cfg.PnLRules.LockoutMinutes.ToString();

            // StopGuard
            var onMissing = string.IsNullOrEmpty(cfg.StopGuard.OnMissing) ? "Flatten" : cfg.StopGuard.OnMissing;
            // Normalise to one of the dropdown items
            var matched = false;
            foreach (var item in _onMissingCombo.Items) { if (string.Equals(item.ToString(), onMissing, StringComparison.OrdinalIgnoreCase)) { _onMissingCombo.SelectedItem = item; matched = true; break; } }
            if (!matched) _onMissingCombo.SelectedIndex = 1; // default Flatten

            _stopAttachSecondsText.Text = cfg.StopGuard.StopAttachSeconds.ToString();
            _expectedCopiesText.Text = cfg.Sizing.ExpectedCopies.ToString();
            _excludedAccountsText.Text = cfg.ExcludedAccounts != null ? string.Join(", ", cfg.ExcludedAccounts) : "";

            // FirmMirror
            _firmMirrorEnabledCheck.IsChecked = cfg.FirmMirror != null && cfg.FirmMirror.Enabled;
            _firmTrailingDDAmountText.Text = cfg.FirmMirror != null && cfg.FirmMirror.TrailingDD != null ? cfg.FirmMirror.TrailingDD.Amount.ToString() : "0";
            _firmDailyLossAmountText.Text = cfg.FirmMirror != null && cfg.FirmMirror.DailyLoss != null ? cfg.FirmMirror.DailyLoss.Amount.ToString() : "0";
        }

        private void OnSaveConfigClick(object sender, RoutedEventArgs e)
        {
            try
            {
                var cfg = _addOn.Config;
                cfg.Mode = _modeCombo.SelectedItem.ToString();
                cfg.EnableWindowGate = _windowGateCheck.IsChecked ?? false;
                cfg.Sizing.MaxContractsPerAccount = int.Parse(_maxContractsAccountText.Text.Trim());
                cfg.Sizing.MaxContractsAggregate = int.Parse(_maxContractsAggregateText.Text.Trim());
                cfg.Overtrading.MaxTradesPerSession = int.Parse(_maxTradesSessionText.Text.Trim());
                cfg.Overtrading.MaxConsecutiveLosses = int.Parse(_maxConsecutiveLossesText.Text.Trim());
                cfg.Overtrading.CooldownMinutes = int.Parse(_cooldownMinutesText.Text.Trim());
                cfg.Overtrading.LockoutMinutes = int.Parse(_lockoutMinutesText.Text.Trim());
                cfg.PnLRules.DailyLossLimit = double.Parse(_dailyLossLimitText.Text.Trim());
                cfg.PnLRules.TrailingDrawdown = double.Parse(_trailingDrawdownText.Text.Trim());
                cfg.PnLRules.LockoutMinutes = int.Parse(_pnlLockoutMinutesText.Text.Trim());
                cfg.StopGuard.OnMissing = _onMissingCombo.SelectedItem.ToString();
                cfg.StopGuard.StopAttachSeconds = int.Parse(_stopAttachSecondsText.Text.Trim());
                cfg.Sizing.ExpectedCopies = int.Parse(_expectedCopiesText.Text.Trim());

                // Excluded accounts from the text box (comma-separated)
                var exclText = _excludedAccountsText.Text.Trim();
                if (string.IsNullOrEmpty(exclText))
                    cfg.ExcludedAccounts = new List<string>();
                else
                    cfg.ExcludedAccounts = exclText.Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries)
                                                   .Select(s => s.Trim())
                                                   .Where(s => !string.IsNullOrEmpty(s))
                                                   .ToList();

                // FirmMirror
                if (cfg.FirmMirror != null)
                {
                    cfg.FirmMirror.Enabled = _firmMirrorEnabledCheck.IsChecked ?? false;
                    if (cfg.FirmMirror.TrailingDD != null)
                        cfg.FirmMirror.TrailingDD.Amount = double.Parse(_firmTrailingDDAmountText.Text.Trim());
                    if (cfg.FirmMirror.DailyLoss != null)
                        cfg.FirmMirror.DailyLoss.Amount = double.Parse(_firmDailyLossAmountText.Text.Trim());
                }

                _addOn.SaveAndReloadConfig(cfg);
                MessageBox.Show("Configuration saved and hot-reloaded successfully!", "Success", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed to parse settings: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void UpdateUI()
        {
            bool isArmed = _addOn.IsArmed;
            string mode = _addOn.Config != null ? _addOn.Config.Mode : "shadow";
            _armedStatusText.Text = isArmed ? string.Format("ARMED ({0})", mode.ToUpper()) : "DISABLED";
            _armedStatusText.Foreground = isArmed ? Brushes.LimeGreen : Brushes.Red;

            var snapshots = _addOn.GetAccountSnapshots();
            var existingAccNames = _cardControls.Keys.ToList();

            string filterText = _searchBox != null ? _searchBox.Text.Trim() : "";
            bool hideInactive = _hideInactiveCheck != null && (_hideInactiveCheck.IsChecked ?? true);

            var filteredSnapshots = new List<RiskGuardAddOn.AccountStateSnapshot>();
            foreach (var snapshot in snapshots)
            {
                // Filter by name
                if (!string.IsNullOrEmpty(filterText) && snapshot.AccountName.IndexOf(filterText, StringComparison.OrdinalIgnoreCase) < 0)
                {
                    continue;
                }

                // Filter by inactive ($0 balance, flat, no trades)
                bool isZeroBal = snapshot.AccountEquity == 0 && snapshot.PositionString == "FLAT" && snapshot.TradesToday == 0;
                if (hideInactive && isZeroBal && snapshot.AccountName != "Sim101") // Keep Sim101 visible by default
                {
                    continue;
                }

                filteredSnapshots.Add(snapshot);
            }

            // Remove cards that are no longer in filtered snapshots
            var filteredNames = new HashSet<string>(filteredSnapshots.Select(s => s.AccountName));
            foreach (var accName in existingAccNames)
            {
                if (!filteredNames.Contains(accName))
                {
                    _cardsPanel.Children.Remove(_cardControls[accName].BorderEl);
                    _cardControls.Remove(accName);
                }
            }

            // Create cards for new filtered snapshots
            foreach (var snapshot in filteredSnapshots)
            {
                if (!_cardControls.ContainsKey(snapshot.AccountName))
                {
                    var card = CreateAccountCard(snapshot.AccountName);
                    _cardControls[snapshot.AccountName] = card;
                    _cardsPanel.Children.Add(card.BorderEl);
                }
            }

            // Update details of all visible cards
            foreach (var snapshot in filteredSnapshots)
            {
                if (_cardControls.TryGetValue(snapshot.AccountName, out var card))
                {
                    card.TitleText.Text = snapshot.AccountName;
                    card.PnlText.Text = string.Format("PnL Today: {0:C} (Realized: {1:C})", snapshot.RealizedPnL + snapshot.UnrealizedPnL, snapshot.RealizedPnL);
                    card.TradesText.Text = string.Format("Trades today: {0} / {1}", snapshot.TradesToday, _addOn.Config.Overtrading.MaxTradesPerSession);
                    card.LossesText.Text = string.Format("Consecutive Losses: {0} / {1}", snapshot.ConsecutiveLosses, _addOn.Config.Overtrading.MaxConsecutiveLosses);
                    card.PositionText.Text = string.Format("Position: {0}", snapshot.PositionString);

                    if (snapshot.IsLockedOut)
                    {
                        card.StatusText.Text = "Locked (EOD)";
                        card.StatusText.Foreground = Brushes.Red;
                        card.BorderEl.BorderBrush = Brushes.Red;
                    }
                    else if (DateTime.UtcNow < snapshot.LockoutUntil)
                    {
                        var remaining = snapshot.LockoutUntil - DateTime.UtcNow;
                        card.StatusText.Text = string.Format("Locked ({0}m)", (int)remaining.TotalMinutes);
                        card.StatusText.Foreground = Brushes.Red;
                        card.BorderEl.BorderBrush = Brushes.Red;
                    }
                    else
                    {
                        // Check if lockout phase is stuck (position open but flatten failing)
                        // We can't access CurrentLockoutPhase from the snapshot, so we check
                        // if the account is locked out AND has an open position AND is not excluded.
                        if ((snapshot.IsLockedOut || DateTime.UtcNow < snapshot.LockoutUntil) &&
                            snapshot.PositionString != "FLAT")
                        {
                            card.StatusText.Text = "LOCKED - STUCK!";
                            card.StatusText.Foreground = Brushes.Red;
                            card.BorderEl.BorderBrush = Brushes.Red;

                            // Show a one-time popup for the stuck lockout
                            if (!_lockoutStuckPopupShown.Contains(snapshot.AccountName))
                            {
                                _lockoutStuckPopupShown.Add(snapshot.AccountName);
                                Dispatcher.BeginInvoke(new Action(() =>
                                {
                                    MessageBox.Show(
                                        string.Format(
                                            "Account {0} is LOCKED OUT but the position ({1}) could not be closed automatically.\n\n" +
                                            "RiskGuard has been trying to flatten for over 30 seconds.\n" +
                                            "MANUAL INTERVENTION REQUIRED:\n" +
                                            "  1. Close the position from the NT8 Chart Trader or DOM\n" +
                                            "  2. Cancel any remaining working orders\n" +
                                            "  3. Click 'Unlock' on the RiskGuard dashboard for this account\n\n" +
                                            "This popup will not repeat for this account until unlocked.",
                                            snapshot.AccountName, snapshot.PositionString),
                                        "RiskGuard: Lockout Stuck - Manual Action Required",
                                        MessageBoxButton.OK, MessageBoxImage.Warning);
                                }));
                            }
                        }
                        else
                        {
                            card.StatusText.Text = "Active";
                            card.StatusText.Foreground = Brushes.LimeGreen;
                            card.BorderEl.BorderBrush = new SolidColorBrush(Color.FromRgb(0, 122, 204));
                        }
                    }

                    // Excluded checkbox state
                    card.ExcludeCheck.IsChecked = snapshot.IsExcluded;
                }
            }
        }

        private CardControls CreateAccountCard(string accountName)
        {
            var card = new CardControls();

            card.BorderEl = new Border
            {
                Background = new SolidColorBrush(Color.FromRgb(40, 40, 40)),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(5),
                Margin = new Thickness(5),
                Padding = new Thickness(10)
            };

            var panel = new StackPanel();

            // Header panel (Title + Status indicator)
            var header = new Grid();
            header.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            header.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

            card.TitleText = new TextBlock { Text = accountName, FontWeight = FontWeights.Bold, Foreground = Brushes.White, FontSize = 12 };
            Grid.SetColumn(card.TitleText, 0);
            header.Children.Add(card.TitleText);

            card.StatusText = new TextBlock { Text = "Active", Foreground = Brushes.LimeGreen, FontSize = 10, VerticalAlignment = VerticalAlignment.Center };
            Grid.SetColumn(card.StatusText, 1);
            header.Children.Add(card.StatusText);

            panel.Children.Add(header);

            // Stats fields
            card.PnlText = new TextBlock { Foreground = Brushes.LightGray, Margin = new Thickness(0, 8, 0, 2) };
            panel.Children.Add(card.PnlText);

            card.TradesText = new TextBlock { Foreground = Brushes.LightGray, Margin = new Thickness(0, 2, 0, 2) };
            panel.Children.Add(card.TradesText);

            card.LossesText = new TextBlock { Foreground = Brushes.LightGray, Margin = new Thickness(0, 2, 0, 2) };
            panel.Children.Add(card.LossesText);

            card.PositionText = new TextBlock { Foreground = Brushes.LightGray, Margin = new Thickness(0, 2, 0, 8) };
            panel.Children.Add(card.PositionText);

            // Action row (Panic button, Unlock button)
            var btnRow = new Grid { Margin = new Thickness(0, 5, 0, 5) };
            btnRow.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            btnRow.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(5) }); // space spacer
            btnRow.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            var panicBtn = new Button 
            { 
                Content = "Panic", 
                Background = new SolidColorBrush(Color.FromRgb(180, 40, 40)), 
                Foreground = Brushes.White, 
                FontWeight = FontWeights.Bold,
                BorderBrush = Brushes.Transparent,
                Padding = new Thickness(0, 3, 0, 3)
            };
            panicBtn.Click += (s, e) => OnCardPanicClick(accountName);
            Grid.SetColumn(panicBtn, 0);
            btnRow.Children.Add(panicBtn);

            var unlockBtn = new Button 
            { 
                Content = "Unlock", 
                Background = new SolidColorBrush(Color.FromRgb(40, 130, 40)), 
                Foreground = Brushes.White, 
                FontWeight = FontWeights.Bold,
                BorderBrush = Brushes.Transparent,
                Padding = new Thickness(0, 3, 0, 3)
            };
            unlockBtn.Click += (s, e) => OnCardUnlockClick(accountName);
            Grid.SetColumn(unlockBtn, 2);
            btnRow.Children.Add(unlockBtn);

            panel.Children.Add(btnRow);

            var lockRow = new Grid { Margin = new Thickness(0, 5, 0, 5) };
            lockRow.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(2, GridUnitType.Star) });
            lockRow.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(5) });
            lockRow.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            var lockComboBox = new ComboBox { Margin = new Thickness(0) };
            lockComboBox.Items.Add("15m");
            lockComboBox.Items.Add("30m");
            lockComboBox.Items.Add("1h");
            lockComboBox.Items.Add("EOD");
            lockComboBox.SelectedIndex = 0;
            Grid.SetColumn(lockComboBox, 0);
            lockRow.Children.Add(lockComboBox);

            var lockBtn = new Button 
            { 
                Content = "Lock", 
                Background = new SolidColorBrush(Color.FromRgb(130, 40, 130)), 
                Foreground = Brushes.White, 
                FontWeight = FontWeights.Bold,
                BorderBrush = Brushes.Transparent,
                Padding = new Thickness(0, 3, 0, 3)
            };
            lockBtn.Click += (s, e) => OnCardLockClick(accountName, lockComboBox.SelectedItem.ToString());
            Grid.SetColumn(lockBtn, 2);
            lockRow.Children.Add(lockBtn);

            panel.Children.Add(lockRow);

            // Excluded Checkbox
            card.ExcludeCheck = new CheckBox 
            { 
                Content = "Exclude from Risk Guard", 
                Foreground = Brushes.LightGray, 
                Margin = new Thickness(0, 5, 0, 0) 
            };
            card.ExcludeCheck.Checked += (s, e) => OnCardExcludeChecked(accountName, true);
            card.ExcludeCheck.Unchecked += (s, e) => OnCardExcludeChecked(accountName, false);
            panel.Children.Add(card.ExcludeCheck);

            card.BorderEl.Child = panel;
            return card;
        }

        private void OnCardPanicClick(string accountName)
        {
            var result = MessageBox.Show(string.Format("Are you sure you want to FLATTEN account {0} and cancel all working orders?", accountName), "Confirm Panic", MessageBoxButton.YesNo, MessageBoxImage.Warning);
            if (result == MessageBoxResult.Yes)
            {
                _addOn.TriggerManualFlatten(accountName);
            }
        }

        private void OnCardUnlockClick(string accountName)
        {
            _addOn.UnlockAccount(accountName);
            _lockoutStuckPopupShown.Remove(accountName); // allow popup to show again if re-locked
            MessageBox.Show(string.Format("Account {0} unlocked/reset successfully.", accountName), "Unlock Success", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void OnCardLockClick(string accountName, string lockType)
        {
            int minutes = 0;
            switch(lockType)
            {
                case "15m": minutes = 15; break;
                case "30m": minutes = 30; break;
                case "1h": minutes = 60; break;
                case "EOD": minutes = -1; break;
                default: minutes = -1; break;
            }

            var result = MessageBox.Show(string.Format("Are you sure you want to LOCK account {0} for {1}? This will flatten open positions.", accountName, lockType), "Confirm Lock", MessageBoxButton.YesNo, MessageBoxImage.Warning);
            if (result == MessageBoxResult.Yes)
            {
                _addOn.LockAccount(accountName, minutes);
                MessageBox.Show(string.Format("Account {0} locked.", accountName), "Lock Success", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }

        private void OnCardExcludeChecked(string accountName, bool isExcluded)
        {
            lock (_addOn.StateLock)
            {
                var cfg = _addOn.Config;
                if (isExcluded)
                {
                    if (!cfg.ExcludedAccounts.Contains(accountName))
                    {
                        cfg.ExcludedAccounts.Add(accountName);
                    }
                }
                else
                {
                    cfg.ExcludedAccounts.Remove(accountName);
                }
                _addOn.SaveAndReloadConfig(cfg);
            }
        }

        private void OnToggleArmedClick(object sender, RoutedEventArgs e)
        {
            _addOn.ToggleArmed();
        }

        private void OnReloadConfigClick(object sender, RoutedEventArgs e)
        {
            _addOn.ReloadConfig();
            LoadConfigIntoUI();
            MessageBox.Show("Configuration successfully reloaded.", "Config Reloaded", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void OnPanicAllClick(object sender, RoutedEventArgs e)
        {
            var result = MessageBox.Show("Are you sure you want to FLATTEN ALL connected accounts and cancel all working orders?", "Confirm Global Panic", MessageBoxButton.YesNo, MessageBoxImage.Warning);
            if (result == MessageBoxResult.Yes)
            {
                _addOn.TriggerManualFlattenAll();
            }
        }
    }

    public class CardControls
    {
        public Border BorderEl { get; set; }
        public TextBlock TitleText { get; set; }
        public TextBlock StatusText { get; set; }
        public TextBlock PnlText { get; set; }
        public TextBlock TradesText { get; set; }
        public TextBlock LossesText { get; set; }
        public TextBlock PositionText { get; set; }
        public CheckBox ExcludeCheck { get; set; }
    }
#endif
}
