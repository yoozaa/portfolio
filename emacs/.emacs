(set-language-environment 'Russian)
(custom-set-variables
 ;; custom-set-variables was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(ansi-color-faces-vector
   [default default default italic underline success warning error])
 '(ansi-color-names-vector
   ["#242424" "#e5786d" "#95e454" "#cae682" "#8ac6f2" "#333366" "#ccaa8f" "#f6f3e8"])
 '(cua-mode t nil (cua-base))
 '(custom-enabled-themes '(wombat))
 '(custom-theme-load-path
   '(custom-theme-directory t "D:\\home\\vlad\\site-lisp\\emacs-color-theme-solarized") t)
 '(ido-ignore-files
   '("\\`CVS/" "\\`#" "\\`.#" "\\`\\.\\./" "\\`\\./" "\\.dcu$"))
 '(inhibit-startup-screen t)
 '(initial-frame-alist '((left . 400) (top . 20) (height . 35) (width . 130)))
 '(jabber-show-offline-contacts nil)
 '(opascal-indent-level 4)
 '(package-archives '(("gnu" . "http://elpa.gnu.org/packages/")))
 '(package-selected-packages
   '(w3 psvn org jabber ergoemacs-mode elpy bookmark+ autopair ack))
 '(pc-selection-mode t)
 '(scroll-bar-mode nil)
 '(show-paren-mode t)
 '(svn-status-hide-externals t)
 '(svn-status-hide-unmodified t)
 '(svn-status-verbose nil)
 '(tab-width 4)
 '(tool-bar-mode nil)
 '(tooltip-mode nil)
 '(truncate-lines t))
(custom-set-faces
 ;; custom-set-faces was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(default ((t (:inherit nil :extend nil :stipple nil :background "#242424" :foreground "#f6f3e8" :inverse-video nil :box nil :strike-through nil :overline nil :underline nil :slant normal :weight normal :height 140 :width normal :foundry "outline" :family "JetBrains Mono")))))

(prefer-coding-system 'cp1251-dos)
(setq search-highlight t)
(setq query-replace-highlight t)
(put 'upcase-region 'disabled nil)
(put 'downcase-region 'disabled nil)
(put 'narrow-to-region 'disabled nil)
(put 'narrow-to-page 'disabled nil)
(setq-default indent-tabs-mode nil)
(standard-display-ascii ?\t "^I")

(setq load-path (cons "~/site-lisp" load-path))
(setq load-path (cons "~/site-lisp/ecb" load-path))

(require 'psvn)
(require 'git)
(require 'dos)
(require 'dos-indent)
;; ToDo исправить
;;(require 'ecb-autoloads)
;; (require 'ecb)

(autoload 'opascal-mode "opascal")
(autoload 'nsis-mode "nsis-mode" "NSIS mode" t)

(modify-coding-system-alist 'file "\.js$" 'utf-8-dos)
(setq auto-mode-alist
      (cons '("\\.\\(pas\\|dpr\\|dpk\\inc\\)$" . opascal-mode) auto-mode-alist))
(setq auto-mode-alist
      (cons '("\\.\\(rfxml\\|cnxml\\)$" . nxml-mode) auto-mode-alist))
(setq auto-mode-alist
      (cons '("\\.bat$" . dos-mode) auto-mode-alist))
(setq auto-mode-alist (append '(("\\.\\([Nn][Ss][Ii]\\)$" .
                                 nsis-mode)) auto-mode-alist))
(setq auto-mode-alist (append '(("\\.\\([Nn][Ss][Hh]\\)$" .
                                 nsis-mode)) auto-mode-alist))

;; .eml files are emails 
(add-to-list 'auto-mode-alist '("\\.eml$" . mail-mode))
;; log files
(add-to-list 'auto-mode-alist '("\\.log$" . auto-revert-mode))



(defun move-line (n)
  "Move the current line up or down by N lines."
  (interactive "p")
  (setq col (current-column))
  (beginning-of-line) (setq start (point))
  (end-of-line) (forward-char) (setq end (point))
  (let ((line-text (delete-and-extract-region start end)))
    (forward-line n)
    (insert line-text)
    ;; restore point to original column in moved line
    (forward-line -1)
    (forward-char col)))

(defun move-line-up (n)
  "Move the current line up by N lines."
  (interactive "p")
  (move-line (if (null n) -1 (- n))))

(defun move-line-down (n)
  "Move the current line down by N lines."
  (interactive "p")
  (move-line (if (null n) 1 n)))

(defun move-region (start end n)
  "Move the current region up or down by N lines."
  (interactive "r\np")
  (let ((line-text (delete-and-extract-region start end)))
    (forward-line n)
    (let ((start (point)))
      (insert line-text)
      (setq deactivate-mark nil)
      (set-mark start))))

(defun move-region-up (start end n)
  "Move the current line up by N lines."
  (interactive "r\np")
  (move-region start end (if (null n) -1 (- n))))

(defun move-region-down (start end n)
  "Move the current line down by N lines."
  (interactive "r\np")
  (move-region start end (if (null n) 1 n)))

(defun search-selection (beg end)
  "search for selected text"
  (interactive "r")
  (let (
        (selection (buffer-substring-no-properties beg end))
        )
    (deactivate-mark)
    (isearch-mode t nil nil nil)
    (isearch-yank-string selection)
    )
  )

(add-hook 'svn-pre-parse-status-hook 'svn-status-parse-fixup-externals-full-path)

(defun svn-status-parse-fixup-externals-full-path ()
 "Subversion 1.7 adds the full path to externals.  This
pre-parse hook fixes it up to look like pre-1.7, allowing
psvn to continue functioning as normal."
 (goto-char (point-min))
 (let (( search-string  (file-truename default-directory) ))
      (save-match-data
        (save-excursion
          (while (re-search-forward search-string (point-max) t)
          (replace-match "" nil nil)
          )))))

(global-set-key (kbd "M-<up>") 'move-line-up)
(global-set-key (kbd "M-<down>") 'move-line-down)
(global-set-key (kbd "C-M-<up>") 'move-region-up)
(global-set-key (kbd "C-M-<down>") 'move-region-down)
(global-set-key (kbd "<C-f>") 'search-selection)


;; (package-initialize)
;; (elpy-enable)

(require 'ido)
(ido-mode t)

;;(load-theme 'solarized t)

;; ToDo исправить
;; (setq-default elpy-default-minor-modes (remove 'highlight-indentation-mode elpy-default-minor-modes))
