(defun _dist2 (p q)
  (+ (expt (- (car p) (car q)) 2.0) (expt (- (cadr p) (cadr q)) 2.0))
)

(defun _getAtt (blk tag / atts a hit)
  (setq hit nil)
  (if (= (vla-get-HasAttributes blk) :vlax-true)
    (progn
      (setq atts (vlax-invoke blk 'GetAttributes))
      (foreach a atts
        (if (= (strcase (vla-get-TagString a)) (strcase tag))
          (setq hit a)
        )
      )
    )
  )
  hit
)

(defun _vpNum (vp / d)
  ;; Viewport number from DXF group 69
  (setq d (entget (vlax-vla-object->ename vp)))
  (cdr (assoc 69 d))
)

(defun _vpViewCenterDXF (vp / d vc)
  ;; View center from DXF group 12 (x y)
  (setq d (entget (vlax-vla-object->ename vp)))
  (setq vc (cdr (assoc 12 d)))
  vc
)

(defun _vpArea (vp / d w h)
  ;; Use ActiveX if available, else DXF 40/41
  (if (and (vlax-property-available-p vp 'Width) (vlax-property-available-p vp 'Height))
    (* (vla-get-Width vp) (vla-get-Height vp))
    (progn
      (setq d (entget (vlax-vla-object->ename vp)))
      (setq w (cdr (assoc 40 d)))
      (setq h (cdr (assoc 41 d)))
      (if (and w h) (* w h) 0.0)
    )
  )
)

(defun _getMainViewportCenter (layBtr / bestObj bestArea obj vpnum area vc)
  ;; pick the largest viewport excluding viewport #1
  (setq bestObj nil bestArea 0.0)

  (vlax-for obj layBtr
    (if (= (vla-get-ObjectName obj) "AcDbViewport")
      (progn
        (setq vpnum (_vpNum obj))
        (if (and vpnum (/= vpnum 1))
          (progn
            (setq area (_vpArea obj))
            (if (> area bestArea)
              (progn (setq bestArea area) (setq bestObj obj))
            )
          )
        )
      )
    )
  )

  (if bestObj
    (_vpViewCenterDXF bestObj)
    nil
  )
)

(defun c:NumberByLayoutModelTag ( / doc lays layList n layObj layBtr vpC ss i e blkObj
                                   best bestD insP att miss blkName tagName d)

  (vl-load-com)

  ;; ===== YOUR SETTINGS =====
  (setq blkName "TITLE_BLOCK_MODEL")  ;; model-space block name
  (setq tagName "PAGE")               ;; model-space attribute TAG
  (setq n 1)                          ;; starting number
  ;; =========================

  (setq doc  (vla-get-ActiveDocument (vlax-get-acad-object)))
  (setq lays (vla-get-Layouts doc))

  ;; Layout list by tab order
  (setq layList '())
  (vlax-for lay lays
    (if (/= (vla-get-Name lay) "Model")
      (setq layList (cons (cons (vla-get-TabOrder lay) (vla-get-Name lay)) layList))
    )
  )
  (setq layList (vl-sort layList '(lambda (a b) (< (car a) (car b)))))

  ;; Select all model-space inserts of the title block
  (setq ss (ssget "X" (list (cons 0 "INSERT") (cons 2 blkName) (cons 410 "Model"))))
  (if (not ss)
    (progn
      (princ (strcat "\nNo model-space inserts found for block: " blkName))
      (princ)
      (exit)
    )
  )

  (setq miss '())

  (foreach item layList
    (setq layObj (vla-item lays (cdr item)))
    (setq layBtr (vla-get-Block layObj))

    (setq vpC (_getMainViewportCenter layBtr))

    (if (not vpC)
      (setq miss (cons (strcat (cdr item) " (no main viewport found)") miss))
      (progn
        ;; Find closest model-space title block insert to viewport view center
        (setq best nil bestD nil)
        (setq i 0)
        (repeat (sslength ss)
          (setq e (ssname ss i))
          (setq blkObj (vlax-ename->vla-object e))
          (setq insP (vlax-safearray->list (vlax-variant-value (vla-get-InsertionPoint blkObj))))
          (setq d (_dist2 vpC insP))
          (if (or (null bestD) (< d bestD))
            (progn (setq best blkObj) (setq bestD d))
          )
          (setq i (1+ i))
        )

        (setq att (_getAtt best tagName))
        (if att
          (progn
            (vla-put-TextString att (if (< n 10) (strcat "0" (itoa n)) (itoa n)))
            (setq n (1+ n))
          )
          (setq miss (cons (strcat (cdr item) " (attribute PAGE not found)") miss))
        )
      )
    )
  )

  (vla-Regen doc acAllViewports)

  (if miss
    (progn
      (princ "\nDone, but some layouts could not be mapped/updated:")
      (foreach m (reverse miss) (princ (strcat "\n - " m)))
    )
    (princ "\nDone: numbered model-space PAGE by layout tab order (mapped via viewport).")
  )

  (princ)
)
;; ===============================
;; Automatic runner (reactors)
;; ===============================

(setq *HB_PageAutoEnabled* nil)
(setq *HB_PageCmdReactor* nil)

(defun HB:_RunPageNumbering ( / )
  (if (and (boundp 'c:NumberByLayoutModelTag) (fboundp 'c:NumberByLayoutModelTag))
    (vl-cmdf "._NumberByLayoutModelTag")
  )
)

(defun HB:_CmdEnded (reactor params / cmd)
  (setq cmd (strcase (car params)))

  ;; Run after common "sheet-changing" and "output" commands
  (if (member cmd
    '("QSAVE" "SAVE" "SAVEAS"
      "PLOT" "PUBLISH" "-PUBLISH"
      "LAYOUT" "-LAYOUT" "MVIEW" "VPORTS"
      "PAGESETUP" "-PAGESETUP"
     )
    )
    (HB:_RunPageNumbering)
  )
)

(defun c:EnableAutoPage ( / )
  (vl-load-com)
  (if (not *HB_PageCmdReactor*)
    (setq *HB_PageCmdReactor*
      (vlr-command-reactor nil
        (list (cons :vlr-commandEnded 'HB:_CmdEnded))
      )
    )
  )
  (setq *HB_PageAutoEnabled* T)
  (princ "\nAuto PAGE numbering is ENABLED (runs on Save/Plot/Layout changes).")
  (princ)
)

(defun c:DisableAutoPage ( / )
  (if *HB_PageCmdReactor*
    (progn
      (vlr-remove *HB_PageCmdReactor*)
      (setq *HB_PageCmdReactor* nil)
    )
  )
  (setq *HB_PageAutoEnabled* nil)
  (princ "\nAuto PAGE numbering is DISABLED.")
  (princ)
)

;; Auto-enable on load:
(c:EnableAutoPage)