# This is the complete clear functionality implementation
# Clear methods for both conversion and combine tabs

    def _clear_files(self):
        """ファイルリストをクリア"""
        try:
            selected_files = []
            for file_path, checkbox in self.file_checkboxes.items():
                if checkbox.get():
                    selected_files.append(file_path)
            
            if selected_files:
                # 選択されたファイルのみ削除
                for file_path in selected_files:
                    if file_path in self.selected_files:
                        self.selected_files.remove(file_path)
                    if file_path in self.file_checkboxes:
                        self.file_checkboxes[file_path].destroy()
                        del self.file_checkboxes[file_path]
                logger.info(f"{len(selected_files)}件のファイルを削除しました")
            else:
                # 選択されたファイルがない場合、全てをクリア
                if self.selected_files:
                    # 確認ダイアログ
                    import tkinter.messagebox as messagebox
                    if messagebox.askyesno("確認", f"全{len(self.selected_files)}件のファイルをクリアしますか？"):
                        self.selected_files.clear()
                        for checkbox in self.file_checkboxes.values():
                            checkbox.destroy()
                        self.file_checkboxes.clear()
                        logger.info("全ファイルをクリアしました")
                    else:
                        return
                else:
                    logger.info("クリアするファイルがありません")
                    return
            
            # UI更新
            self._update_file_list_display()
            self._update_button_states()
            
        except Exception as e:
            logger.error(f"ファイルクリア中にエラーが発生: {str(e)}")
            self._show_error_message("ファイルクリア中にエラーが発生しました。", str(e))

    def _clear_combine_files(self):
        """結合ファイルリストをクリア"""
        try:
            selected_files = []
            for file_path, checkbox in self.combine_checkboxes.items():
                if checkbox.get():
                    selected_files.append(file_path)
            
            if selected_files:
                # 選択されたファイルのみ削除
                for file_path in selected_files:
                    if file_path in self.combine_files:
                        self.combine_files.remove(file_path)
                    if file_path in self.combine_checkboxes:
                        self.combine_checkboxes[file_path].destroy()
                        del self.combine_checkboxes[file_path]
                logger.info(f"{len(selected_files)}件のPDFファイルを削除しました")
            else:
                # 選択されたファイルがない場合、全てをクリア
                if self.combine_files:
                    # 確認ダイアログ
                    import tkinter.messagebox as messagebox
                    if messagebox.askyesno("確認", f"全{len(self.combine_files)}件のPDFファイルをクリアしますか？"):
                        self.combine_files.clear()
                        for checkbox in self.combine_checkboxes.values():
                            checkbox.destroy()
                        self.combine_checkboxes.clear()
                        logger.info("全PDFファイルをクリアしました")
                    else:
                        return
                else:
                    logger.info("クリアするPDFファイルがありません")
                    return
            
            # UI更新
            self._update_combine_list_display()
            self._update_combine_button_states()
            
        except Exception as e:
            logger.error(f"PDFファイルクリア中にエラーが発生: {str(e)}")
            self._show_error_message("PDFファイルクリア中にエラーが発生しました。", str(e))

    def _add_files_to_list(self, file_paths: List[str]) -> None:
        """ファイルリストに追加"""
        valid_files = []
        for file_path in file_paths:
            if FileValidator.is_supported_file(file_path) and FileValidator.is_readable_file(file_path):
                if file_path not in self.selected_files:
                    self.selected_files.append(file_path)
                    valid_files.append(file_path)
                    
                    # チェックボックスを作成
                    filename = os.path.basename(file_path)
                    checkbox = ctk.CTkCheckBox(
                        self.file_list_frame,
                        text=filename,
                        font=("Meiryo UI", 10)
                    )
                    checkbox.pack(anchor="w", pady=2, padx=10)
                    self.file_checkboxes[file_path] = checkbox
        
        if valid_files:
            self._update_file_list_display()
            self._update_button_states()
            logger.info(f"{len(valid_files)}件のファイルを追加しました")

    def _add_combine_files_to_list(self, file_paths: List[str]) -> None:
        """結合ファイルリストに追加"""
        valid_files = []
        for file_path in file_paths:
            if file_path.lower().endswith('.pdf') and FileValidator.is_readable_file(file_path):
                if file_path not in self.combine_files:
                    self.combine_files.append(file_path)
                    valid_files.append(file_path)
                    
                    # チェックボックスを作成（結合用）
                    filename = os.path.basename(file_path)
                    checkbox = ctk.CTkCheckBox(
                        self.combine_list_frame,
                        text=filename,
                        font=("Meiryo UI", 10)
                    )
                    checkbox.pack(anchor="w", pady=2, padx=10)
                    self.combine_checkboxes[file_path] = checkbox
        
        if valid_files:
            self._update_combine_list_display()
            self._update_combine_button_states()
            logger.info(f"{len(valid_files)}件のPDFファイルを追加しました")

    def _update_file_list_display(self) -> None:
        """ファイルリスト表示を更新"""
        if not self.selected_files:
            self.file_list_msg.configure(text="📋 ファイルをドラッグ&ドロップまたは選択してください")
            # 全てのチェックボックスを削除
            for checkbox in self.file_checkboxes.values():
                checkbox.destroy()
            self.file_checkboxes.clear()
        else:
            self.file_list_msg.configure(text=f"📋 {len(self.selected_files)}件のファイルが選択されています")

    def _update_combine_list_display(self) -> None:
        """結合ファイルリスト表示を更新"""
        if not self.combine_files:
            self.combine_list_msg.configure(text="📋 PDFファイルをドラッグ&ドロップまたは選択してください")
            # 全てのチェックボックスを削除
            for checkbox in self.combine_checkboxes.values():
                checkbox.destroy()
            self.combine_checkboxes.clear()
        else:
            self.combine_list_msg.configure(text=f"📋 {len(self.combine_files)}件のPDFファイルが選択されています")

    def _update_button_states(self) -> None:
        """ボタンの状態を更新"""
        has_files = len(self.selected_files) > 0
        
        # 変換開始ボタンとクリアボタンの状態設定
        if has_files and not self.conversion_running:
            self.conversion_start_btn.configure(state="normal")
            self.conversion_clear_btn.configure(state="normal")
        else:
            self.conversion_start_btn.configure(state="disabled")
            if has_files:
                self.conversion_clear_btn.configure(state="normal")
            else:
                self.conversion_clear_btn.configure(state="disabled")

    def _update_combine_button_states(self) -> None:
        """結合ボタンの状態を更新"""
        has_files = len(self.combine_files) > 0
        
        # 結合開始ボタンとクリアボタンの状態設定
        if has_files and not self.combine_running:
            self.combine_start_btn.configure(state="normal")
            self.combine_clear_btn.configure(state="normal")
        else:
            self.combine_start_btn.configure(state="disabled")
            if has_files:
                self.combine_clear_btn.configure(state="normal")
            else:
                self.combine_clear_btn.configure(state="disabled")